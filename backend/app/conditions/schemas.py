"""Typed model of config/arms.yaml.

This slice imports nothing else from the app. Every other slice imports it.
"""
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class ArmId(StrEnum):
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"


class AnswerConfig(BaseModel):
    mode: Literal["passages_only", "reasoned", "direct"]
    socratic_prompt: bool
    max_tokens: int


class SourcesConfig(BaseModel):
    citations: Literal["none", "inline"]
    show_passages: bool
    annotate_quality: bool


class ScaffoldsConfig(BaseModel):
    query_refinement: bool
    source_comparison: bool
    end_reflection: bool


class RetrievalConfig(BaseModel):
    rewrite_query: bool
    decompose: bool
    passes: int = Field(ge=1)
    top_k: int = Field(ge=1)
    rerank: bool


class Arm(BaseModel):
    label: str
    answer: AnswerConfig
    sources: SourcesConfig
    scaffolds: ScaffoldsConfig
    retrieval: RetrievalConfig


class Thresholds(BaseModel):
    low_confidence_rerank_score: float
    conflict_detection_min_sources: int


class ArmsConfig(BaseModel):
    version: str
    arms: dict[ArmId, Arm]
    baseline_arm: ArmId
    thresholds: Thresholds

    content_hash: str = ""

    def get(self, arm_id: ArmId | str) -> Arm:
        return self.arms[ArmId(arm_id)]
