"""Scaffold rules are enabled only by arm configuration."""

from app.conditions.loader import load_arms
from app.conditions.schemas import ArmId
from app.scaffolding.schemas import ScaffoldKind, TriggerContext
from app.scaffolding.triggers import evaluate


def test_scaffold_gates_follow_config() -> None:
    config = load_arms("config/arms.yaml")
    context = TriggerContext(
        top_rerank_score=0.1,
        disagreeing_source_count=2,
        session_ended=True,
    )
    results = {
        arm_id: {item.kind for item in evaluate(context, config.get(arm_id), config.thresholds)}
        for arm_id in ArmId
    }
    assert results[ArmId.A1] == set()
    assert results[ArmId.A2] == {ScaffoldKind.QUERY_REFINEMENT}
    assert results[ArmId.A3] == set(ScaffoldKind)
