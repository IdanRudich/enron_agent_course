"""Eval-only data models (Golden Answers and run results)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AcceptedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Any
    aliases: list[Any] = Field(default_factory=list)


class GoldenAnswer(BaseModel):
    """Official eval-only answer and evidence rules for one challenge."""

    model_config = ConfigDict(extra="forbid")

    accepted_answer: AcceptedAnswer
    evidence_message_ids: list[str]
    evidence_mode: Literal["all", "any", "predicate"]
    evidence_predicate: dict[str, Any] | None = None
    grading_notes: str | None = None


class GoldenChallengeRecord(BaseModel):
    """Full challenge record including eval-only golden answer data."""

    model_config = ConfigDict(extra="forbid")

    id: str
    difficulty: str
    points: int
    prompt: str
    expected_submission: dict[str, Any]
    golden_answer: GoldenAnswer


class GradingDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer_match: bool
    evidence_pass: bool
    evidence_mode: str
    judge_used: bool = False
    judge_equivalent: bool | None = None
    judge_rationale: str | None = None


class ChallengeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_id: str
    difficulty: str
    max_points: int
    points_earned: int
    status: str
    duration_seconds: float
    submission: dict[str, Any] | None = None
    grading: GradingDetail | None = None
    stderr: str = ""
    failure_kind: str | None = None
    raw_stdout: str | None = None


class EvalRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_name: str
    dataset_version: str
    started_at: str
    finished_at: str
    duration_seconds: float
    total_points: int
    max_points: int
    index_dir: str
    challenges: list[ChallengeResult]
