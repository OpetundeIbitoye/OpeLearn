"""Queued PDF ingestion. Blocking parsing and embedding run off the event loop."""

import asyncio
import hashlib
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, ClassVar

from sqlalchemy import select

from app.corpus.chunking import chunk_blocks
from app.corpus.embedding import embed, get_model, model_manifest
from app.corpus.models import Chunk, Document
from app.corpus.parsing import parse_pdf
from app.kernel.config import settings
from app.kernel.db import SessionLocal
from app.kernel.logging import log
from app.kernel.worker import WorkerSettings as InfrastructureWorkerSettings
from app.kernel.worker import check_redis


def prepare(path: Path) -> tuple[list[Any], list[list[float]]]:
    chunks = chunk_blocks(parse_pdf(path), get_model().tokenizer)
    return chunks, embed([chunk.text for chunk in chunks])


async def ingest_pdf(ctx: dict[str, Any], filename: str) -> dict[str, Any]:
    path = (Path(settings.corpus_directory) / filename).resolve()
    if (
        not path.is_relative_to(Path(settings.corpus_directory).resolve())
        or path.suffix.lower() != ".pdf"
    ):
        raise ValueError("PDF path must be inside the configured corpus directory")
    try:
        digest = await asyncio.to_thread(lambda: hashlib.sha256(path.read_bytes()).hexdigest())
        async with SessionLocal() as session:
            existing = await session.scalar(select(Document.id).where(Document.sha256 == digest))
            if existing:
                return {"status": "existing", "document_id": str(existing), "filename": filename}
        chunks, vectors = await asyncio.to_thread(prepare, path)
        manifest = model_manifest()
        async with SessionLocal() as session, session.begin():
            document = Document(filename=filename, sha256=digest)
            session.add(document)
            await session.flush()
            for ordinal, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
                session.add(
                    Chunk(
                        document_id=document.id,
                        ordinal=ordinal,
                        text=chunk.text,
                        section_heading=chunk.section_heading,
                        page_number=chunk.page_number,
                        token_count=chunk.token_count,
                        embedding=vector,
                        embedding_model=settings.embedding_model,
                        embedding_revision=manifest["revision"],
                    )
                )
        log.info(
            "pdf_ingested", filename=filename, chunks=len(chunks), document_id=str(document.id)
        )
        return {
            "status": "ingested",
            "filename": filename,
            "chunks": len(chunks),
            "document_id": str(document.id),
        }
    except Exception:
        log.exception("pdf_ingestion_failed", filename=filename)
        raise


class WorkerSettings(InfrastructureWorkerSettings):
    functions: ClassVar[list[Callable[..., Awaitable[Any]]]] = [check_redis, ingest_pdf]
    max_jobs = 1
    job_timeout = 1800
    max_tries = 1
