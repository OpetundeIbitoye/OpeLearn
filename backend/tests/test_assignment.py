"""Randomisation must be deterministic and balanced within stratum."""

from collections import Counter

from scripts.assign_participants import plan_assignments

from app.conditions.assignment import assign
from app.conditions.schemas import ArmId


def test_deterministic():
    a = assign("p001", cluster="c1", seed=42)
    b = assign("p001", cluster="c1", seed=42)
    assert a == b


def test_balanced_within_cluster():
    assigned: list[tuple[str, str]] = []
    for i in range(90):
        arm = assign(f"p{i:03d}", cluster="c1", seed=42, already_assigned=assigned)
        assigned.append(("c1", arm))
    counts = Counter(arm for _, arm in assigned)
    assert max(counts.values()) - min(counts.values()) <= 1


def test_existing_assignment_is_never_reassigned():
    existing = {"p000": ("c1", ArmId.A3)}
    planned = plan_assignments({"p000": "c1", "p001": "c1"}, seed=42, existing=existing)
    assert "p000" not in planned
    assert existing["p000"] == ("c1", ArmId.A3)
