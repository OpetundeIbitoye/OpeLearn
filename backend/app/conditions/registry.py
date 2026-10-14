"""Resolve an assigned arm, falling back to the configured baseline."""

from app.conditions.schemas import Arm, ArmId, ArmsConfig


def resolve_active_arm(
    config: ArmsConfig,
    assigned_arm: ArmId | None = None,
    forced_arm: ArmId | None = None,
) -> Arm:
    return config.get(forced_arm or assigned_arm or config.baseline_arm)


def affordances(arm: Arm) -> dict[str, bool]:
    return {
        "showSynthesisedAnswer": arm.answer.mode != "passages_only",
        "showInlineCitations": arm.sources.citations == "inline",
        "showRetrievedPassages": arm.sources.show_passages,
        "showQualityAnnotations": arm.sources.annotate_quality,
        "showSocraticPrompt": arm.answer.socratic_prompt,
        "allowQueryRefinement": arm.scaffolds.query_refinement,
        "showSourceComparison": arm.scaffolds.source_comparison,
        "showEndReflection": arm.scaffolds.end_reflection,
    }
