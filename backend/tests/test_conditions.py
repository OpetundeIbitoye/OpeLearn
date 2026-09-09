"""The arms must actually differ in the ways the design says they do.

If this file passes and the manipulation still failed, the problem is the
prompt templates, not the config.
"""
from app.conditions.loader import load_arms
from app.conditions.schemas import ArmId


def test_arms_load():
    cfg = load_arms("config/arms.yaml")
    assert set(cfg.arms) == {ArmId.A1, ArmId.A2, ArmId.A3}
    assert cfg.content_hash


def test_support_is_ordinal():
    """A1 < A2 < A3 on every dimension that defines 'level of support'."""
    cfg = load_arms("config/arms.yaml")
    a1, a2, a3 = (cfg.get(a) for a in (ArmId.A1, ArmId.A2, ArmId.A3))

    # retrieval assistance
    assert not a1.retrieval.rerank and a2.retrieval.rerank and a3.retrieval.rerank
    assert a1.retrieval.passes <= a2.retrieval.passes <= a3.retrieval.passes

    # source transparency
    assert a1.sources.citations == "none"
    assert a2.sources.citations == "inline"
    assert a3.sources.show_passages and not a2.sources.show_passages

    # process scaffolds — count of enabled scaffolds must be non-decreasing
    def n(arm):
        s = arm.scaffolds
        return sum([s.query_refinement, s.source_comparison, s.end_reflection])

    assert n(a1) < n(a2) < n(a3)
