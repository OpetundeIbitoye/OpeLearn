"""Enqueue every PDF; wait for explicit success/failure counts."""
import argparse
import asyncio
from pathlib import Path
from arq import create_pool
from arq.connections import RedisSettings
from app.kernel.config import settings

async def ingest(folder: Path) -> None:
    if not folder.is_dir():
        raise ValueError(f"Corpus directory does not exist: {folder}")
    files = sorted(path for path in folder.rglob("*") if path.suffix.lower() == ".pdf")
    if not files:
        raise ValueError("No PDFs found")
    root = Path(settings.corpus_directory).resolve()
    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    succeeded = failed = 0
    try:
        jobs = []
        for path in files:
            filename = str(path.resolve().relative_to(root))
            jobs.append((filename, await redis.enqueue_job("ingest_pdf", filename)))
        print(f"Enqueued {len(jobs)} PDFs", flush=True)
        for filename, job in jobs:
            try:
                result = await job.result(timeout=7200)
                print(result, flush=True)
                succeeded += 1
            except Exception as error:
                print(f"FAILED {filename}: {error}", flush=True)
                failed += 1
    finally:
        await redis.aclose()
    print(f"PDFs: {len(files)}; succeeded: {succeeded}; failed: {failed}", flush=True)
    if failed:
        raise SystemExit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    asyncio.run(ingest(parser.parse_args().folder))
