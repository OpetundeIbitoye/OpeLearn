"""Deterministic rules gated exclusively by the active arm configuration."""

from app.conditions.schemas import Arm, Thresholds
from app.scaffolding.schemas import ScaffoldKind, ScaffoldPrompt, TriggerContext


def evaluate(context: TriggerContext, arm: Arm, thresholds: Thresholds) -> list[ScaffoldPrompt]:
    prompts: list[ScaffoldPrompt] = []
    if (
        arm.scaffolds.query_refinement
        and context.top_rerank_score is not None
        and context.top_rerank_score < thresholds.low_confidence_rerank_score
    ):
        prompts.append(
            ScaffoldPrompt(
                kind=ScaffoldKind.QUERY_REFINEMENT,
                prompt="Refine the question by naming the concept, context, or evidence you need.",
            )
        )
    if (
        arm.scaffolds.source_comparison
        and context.disagreeing_source_count >= thresholds.conflict_detection_min_sources
    ):
        prompts.append(
            ScaffoldPrompt(
                kind=ScaffoldKind.SOURCE_COMPARISON,
                prompt="Compare the sources' claims, evidence, and limitations before deciding.",
            )
        )
    if arm.scaffolds.end_reflection and context.session_ended:
        prompts.append(
            ScaffoldPrompt(
                kind=ScaffoldKind.END_REFLECTION,
                prompt="Reflect on what changed in your understanding and what remains uncertain.",
            )
        )
    return prompts
