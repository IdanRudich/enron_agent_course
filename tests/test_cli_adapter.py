"""Subprocess tests for the reusable Agent CLI Adapter."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "student_dataset"
MINIMAL_AGENT = PROJECT_ROOT / "tests" / "fixtures" / "minimal_agent.py"
BAD_AGENTS = PROJECT_ROOT / "tests" / "fixtures" / "bad_agents.py"


def run_agent(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(MINIMAL_AGENT), *args],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )


def run_bad_agent(agent_kind: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BAD_AGENTS), agent_kind, *args],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )


class TestMetadataCommand:
    def test_metadata_prints_json_on_stdout(self) -> None:
        result = run_agent("metadata")

        assert result.returncode == 0
        assert result.stdout.strip()
        assert result.stderr == ""

        payload = json.loads(result.stdout)
        assert payload == {"agent_name": "minimal-test-agent"}

    def test_metadata_stdout_is_only_json(self) -> None:
        result = run_agent("metadata")

        json.loads(result.stdout)
        assert "\n" not in result.stdout.strip() or result.stdout.endswith("\n")


class TestIndexCommand:
    def test_index_prints_json_on_stdout(self, tmp_path: Path) -> None:
        index_dir = tmp_path / "index"
        result = run_agent("index", str(DATASET_PATH), str(index_dir))

        assert result.returncode == 0
        assert "indexing" in result.stderr
        assert result.stderr.endswith("\n")

        payload = json.loads(result.stdout)
        assert payload["status"] == "ok"
        assert payload["stats"] == {"indexed": True}


class TestPromptCommand:
    def test_prompt_loads_challenge_and_returns_submission(self, tmp_path: Path) -> None:
        index_dir = tmp_path / "index"
        result = run_agent(
            "prompt",
            str(DATASET_PATH),
            str(index_dir),
            "easy-001",
        )

        assert result.returncode == 0
        assert "solving easy-001" in result.stderr

        payload = json.loads(result.stdout)
        assert payload["challenge_id"] == "easy-001"
        assert payload["answer"] == "stub-answer"
        assert payload["evidence_message_ids"] == ["<stub@example.com>"]

    def test_prompt_public_record_excludes_golden_answer(self, tmp_path: Path) -> None:
        """Minimal agent receives a PublicChallengeRecord without golden_answer."""
        index_dir = tmp_path / "index"

        # Inspect what the agent would get by loading directly.
        from enron_challenge.dataset import load_public_challenge

        challenge = load_public_challenge(DATASET_PATH, "easy-001")
        dumped = challenge.model_dump()
        assert "golden_answer" not in dumped
        assert set(dumped) == {
            "id",
            "difficulty",
            "points",
            "prompt",
            "expected_submission",
        }

        result = run_agent("prompt", str(DATASET_PATH), str(index_dir), "easy-001")
        assert result.returncode == 0

    def test_prompt_unknown_challenge_id(self, tmp_path: Path) -> None:
        index_dir = tmp_path / "index"
        result = run_agent(
            "prompt",
            str(DATASET_PATH),
            str(index_dir),
            "does-not-exist",
        )

        assert result.returncode == 1
        assert result.stdout == ""
        assert "Unknown challenge id" in result.stderr


class TestProtocolErrors:
    def test_invalid_json_exit_code_and_stderr(self, tmp_path: Path) -> None:
        index_dir = tmp_path / "index"
        result = run_bad_agent(
            "invalid-json",
            "prompt",
            str(DATASET_PATH),
            str(index_dir),
            "easy-001",
        )

        assert result.returncode == 2
        assert result.stdout == ""
        assert "invalid json" in result.stderr.lower()

    def test_invalid_submission_exit_code_and_stderr(self, tmp_path: Path) -> None:
        index_dir = tmp_path / "index"
        result = run_bad_agent(
            "invalid-submission",
            "prompt",
            str(DATASET_PATH),
            str(index_dir),
            "easy-001",
        )

        assert result.returncode == 3
        assert result.stdout == ""
        assert "invalid submission" in result.stderr.lower()

    def test_agent_crash_reports_on_stderr(self, tmp_path: Path) -> None:
        index_dir = tmp_path / "index"
        result = run_bad_agent(
            "crash",
            "prompt",
            str(DATASET_PATH),
            str(index_dir),
            "easy-001",
        )

        assert result.returncode == 1
        assert result.stdout == ""
        assert "agent crashed" in result.stderr.lower()


class TestSharedModels:
    def test_public_challenge_record_fields(self) -> None:
        from enron_challenge.dataset import load_public_challenge

        challenge = load_public_challenge(DATASET_PATH, "easy-001")
        assert challenge.id == "easy-001"
        assert challenge.difficulty == "easy"
        assert challenge.points == 2
        assert challenge.prompt
        assert challenge.expected_submission.answer_format
        assert challenge.expected_submission.requires_evidence_message_ids is True
