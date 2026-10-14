"""Reconstruct the archived context and retrieval record for a stored turn."""

import argparse
import asyncio
import hashlib
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.corpus.models import Chunk
from app.kernel.db import SessionLocal, engine
from app.retrieval.models import ExternalCache
from app.retrieval.sources.cache import normalize_query
from app.study.models import RetrievalResult, Turn


async def reconstruct_turn(turn_id: uuid.UUID) -> dict[str, Any]:
    """Return the exact stored prompt plus every archived retrieval input."""

    async with SessionLocal() as database:
        turn = await database.get(Turn, turn_id)
        if turn is None:
            raise ValueError(f"Unknown turn: {turn_id}")
        calculated_hash = hashlib.sha256(turn.prompt.encode()).hexdigest()
        if calculated_hash != turn.prompt_hash:
            raise ValueError("Stored prompt does not match its recorded hash")

        retrieval_rows = (
            await database.execute(
                select(RetrievalResult, Chunk)
                .join(Chunk, Chunk.id == RetrievalResult.chunk_id)
                .where(RetrievalResult.turn_id == turn_id)
                .order_by(RetrievalResult.rank)
            )
        ).all()
        if not retrieval_rows:
            raise ValueError("Turn has no archived retrieval results")
        variants = sorted({result.query_variant for result, _ in retrieval_rows})
        normalised_variants = [normalize_query(variant) for variant in variants]
        cache_rows = (
            (
                await database.scalars(
                    select(ExternalCache)
                    .where(ExternalCache.normalized_query.in_(normalised_variants))
                    .order_by(ExternalCache.provider, ExternalCache.cache_key)
                )
            )
            .unique()
            .all()
        )
        return {
            "turn_id": str(turn.id),
            "session_id": str(turn.session_id) if turn.session_id else None,
            "created_at": turn.created_at.isoformat(),
            "generation_model": turn.generation_model,
            "temperature": turn.temperature,
            "prompt_hash": turn.prompt_hash,
            "prompt": turn.prompt,
            "query": turn.query,
            "answer": turn.answer,
            "retrieval_results": [
                {
                    "rank": result.rank,
                    "chunk_id": str(result.chunk_id),
                    "text": chunk.text,
                    "section_heading": chunk.section_heading,
                    "page_number": chunk.page_number,
                    "query_variant": result.query_variant,
                    "dense_score": result.dense_score,
                    "sparse_score": result.sparse_score,
                    "fused_score": result.fused_score,
                    "rerank_score": result.rerank_score,
                }
                for result, chunk in retrieval_rows
            ],
            "external_cache": [
                {
                    "cache_key": row.cache_key,
                    "provider": row.provider,
                    "normalized_query": row.normalized_query,
                    "raw_payload": row.raw_payload,
                    "fetched_at": row.fetched_at.isoformat(),
                }
                for row in cache_rows
            ],
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("turn_id", type=uuid.UUID)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    replay = await reconstruct_turn(args.turn_id)
    rendered = json.dumps(replay, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n")
        print(args.output)
    else:
        print(rendered)


def main() -> None:
    try:
        asyncio.run(run())
    finally:
        asyncio.run(engine.dispose())


if __name__ == "__main__":
    main()
