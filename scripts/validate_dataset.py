"""Validate pilot completeness and the preregistered manipulation check."""

import asyncio
import sys
from collections import defaultdict
from pathlib import Path

import polars as pl
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.kernel.db import engine
from app.study.export import TABLE_SCHEMAS, TABLES

ARMS = ("A1", "A2", "A3")


def manipulation_check(means: dict[str, float]) -> bool:
    """The preregistered guidance check requires strictly increasing arm means."""

    return all(arm in means for arm in ARMS) and means["A1"] < means["A2"] < means["A3"]


def validate_latest_export(root: Path = Path("analysis/exports")) -> list[str]:
    """Return schema errors for the newest immutable export."""

    exports = (
        sorted(path for path in root.iterdir() if path.is_dir())
        if root.exists()
        else []
    )
    if not exports:
        return ["no timestamped analysis export found"]
    latest = exports[-1]
    errors: list[str] = []
    for table in TABLES:
        path = latest / f"{table}.parquet"
        if not path.exists():
            errors.append(f"{table}: missing {path}")
            continue
        frame = pl.read_parquet(path)
        expected = TABLE_SCHEMAS[table]
        missing = [column for column in expected if column not in frame.columns]
        if missing:
            errors.append(f"{table}: missing columns {missing}")
        for column, data_type in expected.items():
            if column in frame.columns and frame.schema[column] != data_type:
                errors.append(
                    f"{table}.{column}: expected {data_type}, got {frame.schema[column]}"
                )
    return errors


async def scalar(statement: str) -> int:
    async with engine.connect() as connection:
        return int(await connection.scalar(text(statement)) or 0)


async def validate() -> bool:
    async with engine.connect() as connection:
        missing_freeze = int(
            await connection.scalar(
                text(
                    """SELECT count(*) FROM turns WHERE
                    embedding_model IS NULL OR embedding_model = '' OR
                    reranker_model IS NULL OR reranker_model = '' OR
                    generation_model IS NULL OR generation_model = '' OR
                    arms_hash IS NULL OR arms_hash = ''"""
                )
            )
            or 0
        )
        turns_without_retrieval = int(
            await connection.scalar(
                text(
                    """SELECT count(*) FROM turns t
                    WHERE NOT EXISTS (
                        SELECT 1 FROM retrieval_results r WHERE r.turn_id = t.id
                    )"""
                )
            )
            or 0
        )
        sessions_without_events = int(
            await connection.scalar(
                text(
                    """SELECT count(*) FROM sessions s
                    WHERE NOT EXISTS (
                        SELECT 1 FROM interaction_events e WHERE e.session_id = s.id
                    )"""
                )
            )
            or 0
        )
        incomplete_surveys = int(
            await connection.scalar(
                text(
                    """WITH required(instrument) AS (
                        VALUES ('cognitive_load'), ('trust'), ('perceived_support')
                    )
                    SELECT count(*)
                    FROM sessions s CROSS JOIN required r
                    WHERE s.phase = 'treatment' AND s.ended_at IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1 FROM survey_responses sr
                          WHERE sr.session_id = s.id AND sr.instrument = r.instrument
                      )"""
                )
            )
            or 0
        )
        duplicate_arm_participants = int(
            await connection.scalar(
                text(
                    """SELECT count(*) FROM (
                        SELECT id FROM participants
                        GROUP BY id HAVING count(DISTINCT assigned_arm) > 1
                    ) duplicate_assignments"""
                )
            )
            or 0
        )
        invalid_arms = int(
            await connection.scalar(
                text(
                    """SELECT count(*) FROM participants
                    WHERE assigned_arm IS NOT NULL AND assigned_arm NOT IN ('A1', 'A2', 'A3')"""
                )
            )
            or 0
        )
        guidance_rows = (
            (
                await connection.execute(
                    text(
                        """SELECT p.assigned_arm,
                           AVG((sr.responses->>'perceived_guidance')::double precision) AS mean
                    FROM survey_responses sr
                    JOIN sessions s ON s.id = sr.session_id
                    JOIN participants p ON p.id = s.participant_id
                    WHERE sr.instrument = 'perceived_support'
                      AND sr.responses ? 'perceived_guidance'
                      AND p.assigned_arm IS NOT NULL
                    GROUP BY p.assigned_arm
                    ORDER BY p.assigned_arm"""
                    )
                )
            )
            .mappings()
            .all()
        )
        means = {row["assigned_arm"]: float(row["mean"]) for row in guidance_rows}
        arm_rows = (
            (
                await connection.execute(
                    text(
                        """SELECT COALESCE(baseline_cluster, 'unclustered') AS cluster,
                              COALESCE(assigned_arm, 'unassigned') AS arm,
                              count(*) AS count
                       FROM participants
                       GROUP BY baseline_cluster, assigned_arm
                       ORDER BY cluster, arm"""
                    )
                )
            )
            .mappings()
            .all()
        )

    distributions: dict[str, dict[str, int]] = defaultdict(dict)
    for row in arm_rows:
        distributions[row["cluster"]][row["arm"]] = int(row["count"])

    print("Dataset completeness report")
    print(f"  turns missing freeze-list values: {missing_freeze}")
    print(f"  turns with zero retrieval results: {turns_without_retrieval}")
    print(f"  sessions with no events: {sessions_without_events}")
    print(f"  missing required survey responses: {incomplete_surveys}")
    print(f"  participants appearing in multiple arms: {duplicate_arm_participants}")
    print(f"  participants with invalid arms: {invalid_arms}")
    print("Arm distribution overall and per cluster:")
    overall: dict[str, int] = defaultdict(int)
    for cluster, counts in sorted(distributions.items()):
        rendered = ", ".join(f"{arm}={count}" for arm, count in sorted(counts.items()))
        print(f"  {cluster}: {rendered}")
        for arm, count in counts.items():
            overall[arm] += count
    print(
        "  overall: "
        + ", ".join(f"{arm}={count}" for arm, count in sorted(overall.items()))
    )
    print("Mean perceived guidance:")
    for arm in ARMS:
        print(f"  {arm}: {means.get(arm, 'missing')}")
    manipulation_passed = manipulation_check(means)
    print(
        f"Manipulation check A1 < A2 < A3: {'PASS' if manipulation_passed else 'FAIL'}"
    )

    export_errors = validate_latest_export()
    print("Latest export schema: " + ("PASS" if not export_errors else "FAIL"))
    for error in export_errors:
        print(f"  {error}")

    hard_counts = (
        missing_freeze,
        turns_without_retrieval,
        incomplete_surveys,
        duplicate_arm_participants,
        invalid_arms,
    )
    return manipulation_passed and not any(hard_counts) and not export_errors


def main() -> None:
    try:
        valid = asyncio.run(validate())
    finally:
        asyncio.run(engine.dispose())
    if not valid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
