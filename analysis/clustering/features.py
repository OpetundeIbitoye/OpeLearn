"""Extract clustering features from baseline-phase events only."""

from typing import Final

import polars as pl
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

FEATURE_COLUMNS: Final[tuple[str, ...]] = (
    "mean_query_length",
    "query_revision_count",
    "citation_click_rate",
    "passage_expansion_rate",
    "mean_source_dwell_ms",
    "time_to_first_query_seconds",
    "session_duration_seconds",
)


async def build_feature_frame(
    session: AsyncSession, phase: str = "baseline"
) -> pl.DataFrame:
    """Build one feature row per participant from baseline sessions only."""

    if phase != "baseline":
        raise ValueError("Clustering features are restricted to the baseline phase")
    statement = text(
        """
        WITH phase_sessions AS (
            SELECT id, participant_id, started_at, ended_at
            FROM sessions
            WHERE phase = :phase
        ), turn_features AS (
            SELECT ps.participant_id,
                   COUNT(t.id)::double precision AS turn_count,
                   AVG(length(t.query))::double precision AS mean_query_length,
                   MIN(EXTRACT(EPOCH FROM (t.created_at - ps.started_at)))::double precision
                       AS time_to_first_query_seconds
            FROM phase_sessions ps
            LEFT JOIN turns t ON t.session_id = ps.id
            GROUP BY ps.participant_id
        ), event_features AS (
            SELECT ps.participant_id,
                   COUNT(*) FILTER (WHERE e.event_type = 'query_revision')::double precision
                       AS query_revision_count,
                   COUNT(*) FILTER (WHERE e.event_type = 'citation_click')::double precision
                       AS citation_click_count,
                   COUNT(*) FILTER (WHERE e.event_type = 'passage_expand')::double precision
                       AS passage_expansion_count,
                   AVG((e.payload->>'dwell_ms')::double precision) FILTER (
                       WHERE e.event_type IN ('citation_click', 'passage_expand')
                         AND e.payload ? 'dwell_ms'
                   ) AS mean_source_dwell_ms
            FROM phase_sessions ps
            LEFT JOIN interaction_events e ON e.session_id = ps.id
            GROUP BY ps.participant_id
        ), session_features AS (
            SELECT participant_id,
                   AVG(EXTRACT(EPOCH FROM (ended_at - started_at)))::double precision
                       AS session_duration_seconds
            FROM phase_sessions
            WHERE ended_at IS NOT NULL
            GROUP BY participant_id
        )
        SELECT tf.participant_id::text AS participant_id,
               COALESCE(tf.mean_query_length, 0) AS mean_query_length,
               COALESCE(ef.query_revision_count, 0) AS query_revision_count,
               COALESCE(ef.citation_click_count / NULLIF(tf.turn_count, 0), 0)
                   AS citation_click_rate,
               COALESCE(ef.passage_expansion_count / NULLIF(tf.turn_count, 0), 0)
                   AS passage_expansion_rate,
               COALESCE(ef.mean_source_dwell_ms, 0) AS mean_source_dwell_ms,
               COALESCE(tf.time_to_first_query_seconds, 0) AS time_to_first_query_seconds,
               COALESCE(sf.session_duration_seconds, 0) AS session_duration_seconds
        FROM turn_features tf
        JOIN event_features ef USING (participant_id)
        LEFT JOIN session_features sf USING (participant_id)
        ORDER BY tf.participant_id
        """
    )
    rows = (await session.execute(statement, {"phase": phase})).mappings().all()
    if not rows:
        return pl.DataFrame(
            schema={
                "participant_id": pl.String,
                **{name: pl.Float64 for name in FEATURE_COLUMNS},
            }
        )
    return pl.DataFrame([dict(row) for row in rows]).with_columns(
        pl.col(FEATURE_COLUMNS).cast(pl.Float64)
    )
