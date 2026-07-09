"""Unit and integration tests for the answer-equivalence judge."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic_ai.models.test import TestModel

from enron_challenge.models import StudentAgentSubmission
from enron_eval.grader import grade_submission
from enron_eval.judge import (
    AGENT_ENV_VARS,
    ENRON_AGENT_API_KEY,
    ENRON_AGENT_BASE_URL,
    ENRON_AGENT_MODEL,
    ENRON_JUDGE_API_KEY,
    ENRON_JUDGE_BASE_URL,
    ENRON_JUDGE_MODEL,
    JUDGE_ENV_VARS,
    AnswerEquivalenceJudge,
    JudgeConfigError,
    JudgeError,
    JudgeInput,
    JudgeVerdict,
    load_judge_config,
)
from enron_eval.models import AcceptedAnswer, GoldenAnswer
from enron_eval.runner import ChallengeSelector, EvalRunnerError, build_agent_subprocess_env, run_eval

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "student_dataset"
PERFECT_AGENT = PROJECT_ROOT / "tests" / "fixtures" / "perfect_agent.py"
INCORRECT_AGENT = PROJECT_ROOT / "tests" / "fixtures" / "incorrect_agent.py"


def _golden(*, value, aliases=None, evidence_message_ids=None) -> GoldenAnswer:
    return GoldenAnswer(
        accepted_answer=AcceptedAnswer(value=value, aliases=aliases or []),
        evidence_message_ids=evidence_message_ids or ["<a@b>"],
        evidence_mode="all",
    )


def _submission(*, answer, evidence_message_ids=None) -> StudentAgentSubmission:
    return StudentAgentSubmission(
        challenge_id="easy-001",
        answer=answer,
        evidence_message_ids=evidence_message_ids or ["<a@b>"],
    )


def _judge(*, equivalent: bool, rationale: str = "test rationale") -> AnswerEquivalenceJudge:
    model = TestModel(
        custom_output_args=JudgeVerdict(equivalent=equivalent, rationale=rationale),
    )
    return AnswerEquivalenceJudge.from_model(model)


class TestJudgeConfig:
    def test_missing_config_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(ENRON_JUDGE_API_KEY, raising=False)
        monkeypatch.delenv(ENRON_JUDGE_MODEL, raising=False)
        with pytest.raises(JudgeConfigError, match=ENRON_JUDGE_API_KEY):
            load_judge_config()

    def test_partial_config_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ENRON_JUDGE_API_KEY, "test-key")
        monkeypatch.delenv(ENRON_JUDGE_MODEL, raising=False)
        with pytest.raises(JudgeConfigError, match=ENRON_JUDGE_MODEL):
            load_judge_config()

    def test_valid_config_loads(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ENRON_JUDGE_API_KEY, "test-key")
        monkeypatch.setenv(ENRON_JUDGE_MODEL, "MiniMax-M3")
        monkeypatch.delenv(ENRON_JUDGE_BASE_URL, raising=False)
        config = load_judge_config()
        assert config.api_key == "test-key"
        assert config.model == "MiniMax-M3"
        assert config.base_url == "https://api.minimax.io/v1"


class TestAnswerEquivalenceJudge:
    def test_accepts_paraphrase(self) -> None:
        judge = _judge(equivalent=True, rationale="Same phone number formatting.")
        points, detail = grade_submission(
            _submission(answer="(800) 368-3804"),
            _golden(value="1-800-368-3804", aliases=["800-368-3804"]),
            2,
            challenge_prompt="What is the AON phone number?",
            expected_answer_format="phone number",
            judge=judge,
        )
        assert points == 2
        assert detail.judge_used is True
        assert detail.judge_equivalent is True
        assert detail.judge_rationale == "Same phone number formatting."
        assert detail.answer_match is True

    def test_rejects_mismatch(self) -> None:
        judge = _judge(equivalent=False, rationale="Different value entirely.")
        points, detail = grade_submission(
            _submission(answer="completely wrong"),
            _golden(value="1-800-368-3804"),
            2,
            challenge_prompt="What is the AON phone number?",
            expected_answer_format="phone number",
            judge=judge,
        )
        assert points == 0
        assert detail.judge_used is True
        assert detail.judge_equivalent is False
        assert detail.answer_match is False

    def test_not_called_when_deterministic_match(self) -> None:
        judge = _judge(equivalent=True)
        points, detail = grade_submission(
            _submission(answer="1-800-368-3804"),
            _golden(value="1-800-368-3804"),
            2,
            judge=judge,
        )
        assert points == 2
        assert detail.judge_used is False
        assert detail.judge_equivalent is None

    def test_not_called_when_evidence_fails(self) -> None:
        judge = _judge(equivalent=True)
        points, detail = grade_submission(
            _submission(answer="paraphrase", evidence_message_ids=["<wrong>"]),
            _golden(value="expected"),
            2,
            judge=judge,
        )
        assert points == 0
        assert detail.judge_used is False
        assert detail.evidence_pass is False

    def test_judge_input_excludes_evidence_and_email_bodies(self) -> None:
        judge = _judge(equivalent=True)
        evidence_id = "<22322411.1075840045955.JavaMail.evans@thyme>"
        grade_submission(
            _submission(answer="paraphrase", evidence_message_ids=[evidence_id]),
            _golden(value="1-800-368-3804", evidence_message_ids=[evidence_id]),
            2,
            challenge_prompt="What is the AON phone number?",
            expected_answer_format="phone number",
            judge=judge,
        )
        assert judge.last_prompt is not None
        prompt = judge.last_prompt.lower()
        assert "evidence_message_ids" not in prompt
        assert "evidence_mode" not in prompt
        assert "the contact number for aon is" not in prompt
        assert "challenge_prompt" in prompt
        assert "student_answer" in prompt
        assert "expected_answer_value" in prompt

    def test_structured_verdict_from_test_model(self) -> None:
        judge = AnswerEquivalenceJudge.from_model(
            TestModel(
                custom_output_args=JudgeVerdict(
                    equivalent=True,
                    rationale="Structured output works.",
                )
            )
        )
        verdict = judge.evaluate(
            JudgeInput(
                challenge_prompt="Count emails.",
                expected_answer_value=10,
                aliases=[],
                expected_answer_format="integer",
                student_answer="ten messages",
            )
        )
        assert verdict.equivalent is True
        assert verdict.rationale == "Structured output works."


class TestRunnerJudgeIntegration:
    def test_missing_judge_config_fails_before_indexing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.delenv(ENRON_JUDGE_API_KEY, raising=False)
        monkeypatch.delenv(ENRON_JUDGE_MODEL, raising=False)
        with pytest.raises(EvalRunnerError, match=ENRON_JUDGE_API_KEY):
            run_eval(
                [sys.executable, str(PERFECT_AGENT)],
                DATASET_PATH,
                output_dir=tmp_path / "results",
                selector=ChallengeSelector(challenge_ids=["easy-001"]),
            )

    def test_mid_run_judge_failure_aborts_eval(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        from enron_eval import runner as runner_module

        monkeypatch.setenv(ENRON_JUDGE_API_KEY, "test-key")
        monkeypatch.setenv(ENRON_JUDGE_MODEL, "MiniMax-M3")

        failing_judge = MagicMock()
        failing_judge.evaluate.side_effect = JudgeError("Judge API unavailable")

        def _failing_from_config(_config):
            return failing_judge

        monkeypatch.setattr(
            AnswerEquivalenceJudge, "from_config", staticmethod(_failing_from_config)
        )
        with pytest.raises(EvalRunnerError, match="Judge API unavailable"):
            run_eval(
                [sys.executable, str(INCORRECT_AGENT)],
                DATASET_PATH,
                output_dir=tmp_path / "results",
                selector=runner_module.ChallengeSelector(challenge_ids=["easy-001"]),
            )

    def test_agent_subprocess_env_strips_judge_vars(self) -> None:
        base = {
            ENRON_JUDGE_API_KEY: "judge-secret",
            ENRON_JUDGE_MODEL: "judge-model",
            ENRON_JUDGE_BASE_URL: "https://judge.example/v1",
            ENRON_AGENT_API_KEY: "agent-secret",
            ENRON_AGENT_MODEL: "agent-model",
            ENRON_AGENT_BASE_URL: "https://agent.example/v1",
            "PATH": "/usr/bin",
        }
        sanitized = build_agent_subprocess_env(base)
        assert ENRON_JUDGE_API_KEY not in sanitized
        assert ENRON_JUDGE_MODEL not in sanitized
        assert ENRON_JUDGE_BASE_URL not in sanitized
        assert sanitized[ENRON_AGENT_API_KEY] == "agent-secret"
        assert sanitized[ENRON_AGENT_MODEL] == "agent-model"
        assert sanitized[ENRON_AGENT_BASE_URL] == "https://agent.example/v1"

    def test_agent_subprocess_does_not_receive_judge_credentials(self) -> None:
        base = {
            ENRON_JUDGE_API_KEY: "judge-secret",
            ENRON_JUDGE_MODEL: "judge-model",
            ENRON_JUDGE_BASE_URL: "https://judge.example/v1",
            ENRON_AGENT_API_KEY: "agent-secret",
            ENRON_AGENT_MODEL: "agent-model",
            ENRON_AGENT_BASE_URL: "https://agent.example/v1",
            "PATH": os.environ.get("PATH", ""),
        }
        sanitized = build_agent_subprocess_env(base)
        keys = list(JUDGE_ENV_VARS) + list(AGENT_ENV_VARS)
        probe = (
            "import json, os; "
            f"keys = {json.dumps(keys)}; "
            "print(json.dumps({k: os.environ.get(k) for k in keys}))"
        )

        result = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            env=sanitized,
        )
        assert result.returncode == 0, result.stderr
        env_seen = json.loads(result.stdout)
        assert env_seen[ENRON_JUDGE_API_KEY] is None
        assert env_seen[ENRON_JUDGE_MODEL] is None
        assert env_seen[ENRON_JUDGE_BASE_URL] is None
        assert env_seen[ENRON_AGENT_API_KEY] == "agent-secret"
        assert env_seen[ENRON_AGENT_MODEL] == "agent-model"
        assert env_seen[ENRON_AGENT_BASE_URL] == "https://agent.example/v1"
