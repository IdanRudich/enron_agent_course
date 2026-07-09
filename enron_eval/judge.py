"""Answer-equivalence judge fallback using PydanticAI."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

DEFAULT_JUDGE_BASE_URL = "https://api.minimax.io/v1"

ENRON_JUDGE_API_KEY = "ENRON_JUDGE_API_KEY"
ENRON_JUDGE_MODEL = "ENRON_JUDGE_MODEL"
ENRON_JUDGE_BASE_URL = "ENRON_JUDGE_BASE_URL"

ENRON_AGENT_API_KEY = "ENRON_AGENT_API_KEY"
ENRON_AGENT_MODEL = "ENRON_AGENT_MODEL"
ENRON_AGENT_BASE_URL = "ENRON_AGENT_BASE_URL"

JUDGE_ENV_VARS = (ENRON_JUDGE_API_KEY, ENRON_JUDGE_MODEL, ENRON_JUDGE_BASE_URL)
AGENT_ENV_VARS = (ENRON_AGENT_API_KEY, ENRON_AGENT_MODEL, ENRON_AGENT_BASE_URL)

_JUDGE_SYSTEM_PROMPT = (
    "You are an answer-equivalence judge for an email research challenge. "
    "Decide whether the student answer is semantically equivalent to the expected "
    "answer, considering accepted aliases. Ignore formatting differences when the "
    "meaning matches. Do not evaluate evidence or email content beyond what is "
    "provided in the prompt and answers."
)


class JudgeConfigError(Exception):
    """Required judge configuration is missing."""


class JudgeError(Exception):
    """Answer-equivalence judge failed during evaluation."""


@dataclass(frozen=True)
class JudgeConfig:
    api_key: str
    model: str
    base_url: str


class JudgeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_prompt: str
    expected_answer_value: Any
    aliases: list[Any]
    expected_answer_format: str
    student_answer: Any


class JudgeVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    equivalent: bool
    rationale: str


def load_judge_config() -> JudgeConfig:
    """Load judge configuration from environment variables."""
    api_key = os.environ.get(ENRON_JUDGE_API_KEY)
    model = os.environ.get(ENRON_JUDGE_MODEL)
    missing = [
        name
        for name, value in (
            (ENRON_JUDGE_API_KEY, api_key),
            (ENRON_JUDGE_MODEL, model),
        )
        if not value
    ]
    if missing:
        raise JudgeConfigError(
            f"Missing required judge configuration: {', '.join(missing)}"
        )
    base_url = os.environ.get(ENRON_JUDGE_BASE_URL, DEFAULT_JUDGE_BASE_URL)
    return JudgeConfig(api_key=api_key, model=model, base_url=base_url)


class AnswerEquivalenceJudge:
    """LLM fallback for semantically equivalent answers after evidence passes."""

    def __init__(self, agent: Agent[None, JudgeVerdict]) -> None:
        self._agent = agent
        self.last_prompt: str | None = None

    @classmethod
    def from_config(cls, config: JudgeConfig) -> AnswerEquivalenceJudge:
        model = OpenAIChatModel(
            config.model,
            provider=OpenAIProvider(
                base_url=config.base_url,
                api_key=config.api_key,
            ),
        )
        return cls.from_model(model)

    @classmethod
    def from_model(cls, model: Model) -> AnswerEquivalenceJudge:
        agent: Agent[None, JudgeVerdict] = Agent(
            model,
            output_type=JudgeVerdict,
            system_prompt=_JUDGE_SYSTEM_PROMPT,
        )
        return cls(agent)

    def evaluate(self, judge_input: JudgeInput) -> JudgeVerdict:
        prompt = _format_judge_prompt(judge_input)
        self.last_prompt = prompt
        try:
            result = self._agent.run_sync(
                prompt,
                model_settings={"temperature": 0},
            )
        except Exception as exc:
            raise JudgeError(f"Answer-equivalence judge failed: {exc}") from exc
        return result.output


def _format_judge_prompt(judge_input: JudgeInput) -> str:
    payload = {
        "challenge_prompt": judge_input.challenge_prompt,
        "expected_answer_value": judge_input.expected_answer_value,
        "accepted_aliases": judge_input.aliases,
        "expected_answer_format": judge_input.expected_answer_format,
        "student_answer": judge_input.student_answer,
    }
    return (
        "Compare the student answer to the expected answer for equivalence.\n\n"
        f"{json.dumps(payload, indent=2, ensure_ascii=False)}"
    )
