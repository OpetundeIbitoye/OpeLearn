"""Cluster eligible baseline participants, then assign arms within each cluster."""

import argparse
import asyncio
import hashlib
import json
import sys
import uuid
from collections import Counter, defaultdict
from pathlib import Path

from sqlalchemy import func, select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.conditions.assignment import assign
from app.conditions.schemas import ArmId
from app.kernel.config import settings
from app.kernel.db import SessionLocal, engine
from app.study.models import Participant, StudySession

from analysis.clustering.cluster import ClusterResult, fit_clusters
from analysis.clustering.features import build_feature_frame


def plan_assignments(
    clusters: dict[str, str],
    seed: int,
    existing: dict[str, tuple[str, ArmId]],
) -> dict[str, ArmId]:
    """Plan deterministic assignments without changing already assigned participants."""

    assigned = list(existing.values())
    planned: dict[str, ArmId] = {}
    for participant_id in sorted(clusters, key=lambda value: (clusters[value], value)):
        if participant_id in existing:
            continue
        cluster = clusters[participant_id]
        arm = assign(participant_id, cluster, seed, assigned)
        planned[participant_id] = arm
        assigned.append((cluster, arm))
    return planned


def clustering_run_id(result: ClusterResult, seed: int) -> uuid.UUID:
    """Derive a stable run ID from inputs and fitted labels."""

    payload = json.dumps(
        {"labels": result.labels, "report": result.report, "seed": seed},
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return uuid.UUID(digest[:32])


async def run(dry_run: bool) -> None:
    async with SessionLocal() as database:
        completed = (
            select(
                StudySession.participant_id.label("participant_id"),
                func.count(StudySession.id).label("task_count"),
            )
            .where(StudySession.phase == "baseline", StudySession.ended_at.is_not(None))
            .group_by(StudySession.participant_id)
            .subquery()
        )
        participants = list(
            (
                await database.scalars(
                    select(Participant)
                    .join(completed, completed.c.participant_id == Participant.id)
                    .where(completed.c.task_count >= settings.baseline_tasks_required)
                    .order_by(Participant.id)
                )
            ).all()
        )
        eligible_ids = {str(participant.id) for participant in participants}
        frame = await build_feature_frame(database)
        frame = frame.filter(frame["participant_id"].is_in(eligible_ids))
        result = fit_clusters(frame, settings.randomization_seed)
        run_id = clustering_run_id(result, settings.randomization_seed)

        existing = {
            str(participant.id): (
                participant.baseline_cluster,
                ArmId(participant.assigned_arm),
            )
            for participant in participants
            if participant.baseline_cluster is not None
            and participant.assigned_arm is not None
        }
        effective_clusters = dict(result.labels)
        effective_clusters.update(
            {
                participant_id: cluster
                for participant_id, (cluster, _) in existing.items()
            }
        )
        planned = plan_assignments(
            effective_clusters, settings.randomization_seed, existing
        )

        cluster_sizes = Counter(effective_clusters.values())
        print("Cluster sizes:")
        for cluster, size in sorted(cluster_sizes.items()):
            print(f"  {cluster}: {size}")

        distribution: dict[str, Counter[ArmId]] = defaultdict(Counter)
        for participant_id, (cluster, arm) in existing.items():
            if participant_id in effective_clusters:
                distribution[cluster][arm] += 1
        for participant_id, arm in planned.items():
            distribution[effective_clusters[participant_id]][arm] += 1
        print("Arm distribution within each cluster:")
        for cluster in sorted(cluster_sizes):
            counts = distribution[cluster]
            rendered = ", ".join(f"{arm.value}={counts[arm]}" for arm in ArmId)
            print(f"  {cluster}: {rendered}")

        if dry_run:
            await database.rollback()
            return

        by_id = {str(participant.id): participant for participant in participants}
        for participant_id, arm in planned.items():
            participant = by_id[participant_id]
            participant.baseline_cluster = effective_clusters[participant_id]
            participant.assigned_arm = arm.value
            participant.assignment_seed = settings.randomization_seed
            participant.clustering_run_id = run_id
        await database.commit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="Print assignments without writing"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(run(args.dry_run))
    finally:
        asyncio.run(engine.dispose())


if __name__ == "__main__":
    main()
