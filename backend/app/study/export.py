"""Export immutable, explicitly typed analysis snapshots."""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl
from sqlalchemy import text

from app.kernel.db import engine

TABLES = (
    "participants",
    "sessions",
    "turns",
    "retrieval_results",
    "interaction_events",
    "survey_responses",
    "external_cache",
)

TABLE_SCHEMAS: dict[str, dict[str, pl.DataType]] = {
    "participants": {
        "id": pl.String,
        "pseudonym": pl.String,
        "consent_version": pl.String,
        "consented_at": pl.Datetime(time_zone="UTC"),
        "baseline_cluster": pl.String,
        "assigned_arm": pl.String,
        "assignment_seed": pl.Int64,
        "clustering_run_id": pl.String,
        "created_at": pl.Datetime(time_zone="UTC"),
    },
    "sessions": {
        "id": pl.String,
        "participant_id": pl.String,
        "phase": pl.String,
        "started_at": pl.Datetime(time_zone="UTC"),
        "ended_at": pl.Datetime(time_zone="UTC"),
    },
    "turns": {
        "id": pl.String,
        "query": pl.String,
        "answer": pl.String,
        "prompt": pl.String,
        "prompt_hash": pl.String,
        "embedding_model": pl.String,
        "reranker_model": pl.String,
        "generation_model": pl.String,
        "arms_hash": pl.String,
        "temperature": pl.Float64,
        "latency_ms": pl.Int64,
        "input_tokens": pl.Int64,
        "output_tokens": pl.Int64,
        "created_at": pl.Datetime(time_zone="UTC"),
        "session_id": pl.String,
    },
    "retrieval_results": {
        "id": pl.String,
        "turn_id": pl.String,
        "chunk_id": pl.String,
        "rank": pl.Int64,
        "dense_score": pl.Float64,
        "sparse_score": pl.Float64,
        "fused_score": pl.Float64,
        "rerank_score": pl.Float64,
        "query_variant": pl.String,
        "created_at": pl.Datetime(time_zone="UTC"),
    },
    "interaction_events": {
        "id": pl.String,
        "session_id": pl.String,
        "event_type": pl.String,
        "payload": pl.String,
        "client_timestamp": pl.Datetime(time_zone="UTC"),
        "received_at": pl.Datetime(time_zone="UTC"),
    },
    "survey_responses": {
        "id": pl.String,
        "session_id": pl.String,
        "instrument": pl.String,
        "trigger": pl.String,
        "responses": pl.String,
        "submitted_at": pl.Datetime(time_zone="UTC"),
    },
    "external_cache": {
        "cache_key": pl.String,
        "provider": pl.String,
        "normalized_query": pl.String,
        "raw_payload": pl.String,
        "fetched_at": pl.Datetime(time_zone="UTC"),
    },
}


def _normalise_value(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return value


def typed_frame(table: str, rows: list[dict[str, Any]]) -> pl.DataFrame:
    """Build a stable Parquet schema even when a table has no rows."""

    schema = TABLE_SCHEMAS[table]
    normalised = [{column: _normalise_value(row.get(column)) for column in schema} for row in rows]
    return pl.DataFrame(normalised, schema=schema, strict=False)


async def export_tables(root: Path = Path("analysis/exports")) -> Path:
    destination = root / datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    destination.mkdir(parents=True, exist_ok=False)
    async with engine.connect() as connection:
        for table in TABLES:
            result = await connection.execute(text(f'SELECT * FROM "{table}"'))
            rows = [dict(row) for row in result.mappings()]
            frame = typed_frame(table, rows)
            frame.write_parquet(destination / f"{table}.parquet")
    return destination
