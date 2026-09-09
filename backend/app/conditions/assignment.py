"""Deterministic, seeded, stratified assignment.

Stratification is by baseline cluster (see design doc, Flag 01): participants
are clustered on baseline-phase behaviour BEFORE they are assigned, so the
moderator is not downstream of the manipulation.

Deterministic on (seed, participant_id) so any assignment can be reproduced
from the recorded seed alone.
"""
import hashlib
from collections import Counter
from collections.abc import Sequence

from app.conditions.schemas import ArmId

ARMS: tuple[ArmId, ...] = (ArmId.A1, ArmId.A2, ArmId.A3)


def _stable_rank(seed: int, participant_id: str) -> int:
    h = hashlib.sha256(f"{seed}:{participant_id}".encode()).hexdigest()
    return int(h, 16)


def assign(
    participant_id: str,
    cluster: str,
    seed: int,
    already_assigned: Sequence[tuple[str, ArmId]] = (),
) -> ArmId:
    """Return the arm for one participant, balancing within their cluster.

    `already_assigned` is [(cluster, arm), ...] for everyone enrolled so far.
    Picks the least-filled arm within this participant's stratum; ties broken
    deterministically by a hash of (seed, participant_id).
    """
    counts = Counter(arm for c, arm in already_assigned if c == cluster)
    fewest = min(counts.get(a, 0) for a in ARMS)
    candidates = [a for a in ARMS if counts.get(a, 0) == fewest]
    return candidates[_stable_rank(seed, participant_id) % len(candidates)]
