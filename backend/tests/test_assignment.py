"""Randomisation must be deterministic and balanced within stratum."""
from collections import Counter

from app.conditions.assignment import assign


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
