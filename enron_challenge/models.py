"""Shared protocol data models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExpectedSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer_format: str
    requires_evidence_message_ids: bool


class PublicChallengeRecord(BaseModel):
    """Student-facing challenge record without golden answer internals."""

    model_config = ConfigDict(extra="forbid")

    id: str
    difficulty: str
    points: int
    prompt: str
    expected_submission: ExpectedSubmission


class StudentAgentSubmission(BaseModel):
    """Answer returned by a student agent for one challenge."""

    model_config = ConfigDict(extra="allow")

    challenge_id: str
    answer: Any
    evidence_message_ids: list[str]

    @field_validator("evidence_message_ids")
    @classmethod
    def evidence_must_be_string_list(cls, value: list[str]) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("evidence_message_ids must be a list")
        for item in value:
            if not isinstance(item, str):
                raise ValueError("evidence_message_ids must contain only strings")
        return value


class AgentMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_name: str


class IndexResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str
    stats: dict[str, Any] | None = None
