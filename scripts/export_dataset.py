"""Produce a timestamped Parquet analysis dataset."""

import asyncio

from app.study.export import export_tables


async def main() -> None:
    destination = await export_tables()
    print(destination)


if __name__ == "__main__":
    asyncio.run(main())
