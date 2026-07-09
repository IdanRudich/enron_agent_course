"""Subprocess tests for eval failure handling and per-challenge diagnostics."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "student_dataset"
FIXTURES = PROJECT_ROOT / "tests" / "fixtures"


def run_enron_eval(
    agent_path: Path,
    *,
    output_dir: Path | None = None,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        "-m",
        "enron_eval.cli",
        "--agent-cmd",
        sys.executable,
        str(agent_path),
        "--dataset",
        str(DATASET_PATH),
    ]
    if output_dir is not None:
        cmd.extend(["--output-dir", str(output_dir)])
    cmd.append("--skip-judge")
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )


class TestEvalFailures:
    def test_index_failure_aborts_before_prompts(self, tmp_path: Path) -> None:
        result = run_enron_eval(
            FIXTURES / "index_fail_agent.py",
            output_dir=tmp_path / "results",
        )

        assert result.returncode == 1
        assert "Agent index failed" in result.stderr
        assert "prompt should not run" not in result.stderr
        assert not (tmp_path / "results" / "results.json").exists()

    def test_metadata_failure_aborts_before_evaluation(self, tmp_path: Path) -> None:
        result = run_enron_eval(
            FIXTURES / "metadata_fail_agent.py",
            output_dir=tmp_path / "results",
        )

        assert result.returncode == 1
        assert "Agent metadata failed" in result.stderr
        assert not (tmp_path / "results" / "results.json").exists()

    def test_crash_agent_records_per_challenge_failures(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "results"
        result = run_enron_eval(
            FIXTURES / "crash_agent.py",
            output_dir=output_dir,
            extra_args=["--challenge-id", "easy-001", "--challenge-id", "easy-002"],
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
        assert len(payload["challenges"]) == 2
        for challenge in payload["challenges"]:
            assert challenge["status"] == "crash"
            assert challenge["failure_kind"] == "crash"
            assert challenge["points_earned"] == 0
            assert "crashing on" in challenge["stderr"]

    def test_timeout_agent_records_per_challenge_failure(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "results"
        result = run_enron_eval(
            FIXTURES / "timeout_agent.py",
            output_dir=output_dir,
            extra_args=["--challenge-id", "easy-001", "--timeout", "2"],
        )

        assert result.returncode == 0, result.stderr
        challenge = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))[
            "challenges"
        ][0]
        assert challenge["status"] == "timeout"
        assert challenge["failure_kind"] == "timeout"
        assert challenge["points_earned"] == 0

    def test_invalid_json_preserves_raw_stdout(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "results"
        result = run_enron_eval(
            FIXTURES / "invalid_json_agent.py",
            output_dir=output_dir,
            extra_args=["--challenge-id", "easy-001"],
        )

        assert result.returncode == 0, result.stderr
        challenge = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))[
            "challenges"
        ][0]
        assert challenge["status"] == "invalid_json"
        assert challenge["failure_kind"] == "invalid_json"
        assert challenge["raw_stdout"].strip() == "not valid json {{{"
        assert "invalid json on easy-001" in challenge["stderr"]

    def test_invalid_submission_records_failure(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "results"
        result = run_enron_eval(
            FIXTURES / "invalid_submission_agent.py",
            output_dir=output_dir,
            extra_args=["--challenge-id", "easy-001"],
        )

        assert result.returncode == 0, result.stderr
        challenge = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))[
            "challenges"
        ][0]
        assert challenge["status"] == "invalid_submission"
        assert challenge["failure_kind"] == "invalid_submission"
        assert challenge["points_earned"] == 0

    def test_incorrect_agent_scores_zero(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "results"
        result = run_enron_eval(
            FIXTURES / "incorrect_agent.py",
            output_dir=output_dir,
            extra_args=["--challenge-id", "easy-001"],
        )

        assert result.returncode == 0, result.stderr
        challenge = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))[
            "challenges"
        ][0]
        assert challenge["status"] == "incorrect"
        assert challenge["points_earned"] == 0
        assert challenge["grading"]["answer_match"] is False
        assert challenge["grading"]["evidence_pass"] is True

    def test_bad_evidence_agent_scores_zero(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "results"
        result = run_enron_eval(
            FIXTURES / "bad_evidence_agent.py",
            output_dir=output_dir,
            extra_args=["--challenge-id", "easy-001"],
        )

        assert result.returncode == 0, result.stderr
        challenge = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))[
            "challenges"
        ][0]
        assert challenge["status"] == "incorrect"
        assert challenge["points_earned"] == 0
        assert challenge["grading"]["answer_match"] is True
        assert challenge["grading"]["evidence_pass"] is False

    def test_prompt_failures_continue_to_remaining_challenges(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "results"
        result = run_enron_eval(
            FIXTURES / "crash_agent.py",
            output_dir=output_dir,
            extra_args=[
                "--challenge-id",
                "easy-001",
                "--challenge-id",
                "easy-002",
                "--challenge-id",
                "easy-003",
            ],
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
        assert [c["challenge_id"] for c in payload["challenges"]] == [
            "easy-001",
            "easy-002",
            "easy-003",
        ]
        assert payload["total_points"] == 0
        assert payload["max_points"] == sum(c["max_points"] for c in payload["challenges"])

    def test_stderr_preserved_for_every_prompt(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "results"
        result = run_enron_eval(
            FIXTURES / "incorrect_agent.py",
            output_dir=output_dir,
            extra_args=["--challenge-id", "easy-001", "--challenge-id", "easy-002"],
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
        for challenge in payload["challenges"]:
            assert challenge["stderr"]
            assert "wrong answer for" in challenge["stderr"]
