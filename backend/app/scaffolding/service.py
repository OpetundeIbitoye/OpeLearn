"""Public scaffold evaluation service."""

from app.conditions.schemas import Arm, Thresholds
from app.scaffolding.schemas import ScaffoldPrompt, TriggerContext
from app.scaffolding.triggers import evaluate


def evaluate_scaffolds(
    context: TriggerContext, arm: Arm, thresholds: Thresholds
) -> list[ScaffoldPrompt]:
    return evaluate(context, arm, thresholds)
