"""Subprocess tests for eval challenge selection and output paths."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "student_dataset"
PERFECT_AGENT = PROJECT_ROOT / "tests" / "fixtures" / "perfect_agent.py"


def run_enron_eval(
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
        str(PERFECT_AGENT),
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


class TestEvalSelectors:
    def test_default_runs_all_challenges(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "results"
        result = run_enron_eval(output_dir=output_dir)

        assert result.returncode == 0, result.stderr
        payload = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
        assert len(payload["challenges"]) == 28
        assert payload["max_points"] == 142

    def test_all_flag_runs_all_challenges(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "results"
        result = run_enron_eval(output_dir=output_dir, extra_args=["--all"])

        assert result.returncode == 0, result.stderr
        payload = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
        assert len(payload["challenges"]) == 28

    def test_all_mutually_exclusive_with_challenge_id(self) -> None:
        result = run_enron_eval(extra_args=["--all", "--challenge-id", "easy-001"])

        assert result.returncode != 0
        assert "not allowed with" in result.stderr.lower()

    def test_all_mutually_exclusive_with_difficulty(self) -> None:
        result = run_enron_eval(extra_args=["--all", "--difficulty", "easy"])

        assert result.returncode != 0
        assert "not allowed with" in result.stderr.lower()

    def test_challenge_id_selection(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "results"
        result = run_enron_eval(
            output_dir=output_dir,
            extra_args=["--challenge-id", "easy-001", "--challenge-id", "medium-003"],
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
        assert [c["challenge_id"] for c in payload["challenges"]] == [
            "easy-001",
            "medium-003",
        ]

    def test_repeated_challenge_id_selection(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "results"
        result = run_enron_eval(
            output_dir=output_dir,
            extra_args=[
                "--challenge-id",
                "easy-001",
                "--challenge-id",
                "easy-001",
            ],
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
        assert [c["challenge_id"] for c in payload["challenges"]] == ["easy-001", "easy-001"]
        assert payload["max_points"] == 4

    def test_difficulty_selection(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "results"
        result = run_enron_eval(
            output_dir=output_dir,
            extra_args=["--difficulty", "easy"],
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
        assert len(payload["challenges"]) == 10
        assert all(c["difficulty"] == "easy" for c in payload["challenges"])

    def test_repeated_difficulty_selection(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "results"
        result = run_enron_eval(
            output_dir=output_dir,
            extra_args=["--difficulty", "easy", "--difficulty", "medium"],
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
        assert len(payload["challenges"]) == 20
        difficulties = {c["difficulty"] for c in payload["challenges"]}
        assert difficulties == {"easy", "medium"}

    def test_unknown_challenge_id_fails_before_prompts(self, tmp_path: Path) -> None:
        result = run_enron_eval(
            output_dir=tmp_path / "results",
            extra_args=["--challenge-id", "does-not-exist"],
        )

        assert result.returncode == 1
        assert "Unknown challenge id: does-not-exist" in result.stderr
        assert not (tmp_path / "results" / "results.json").exists()

    def test_default_output_dir_uses_slugified_agent_name(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "enron_eval.cli",
                "--agent-cmd",
                sys.executable,
                str(PERFECT_AGENT),
                "--dataset",
                str(DATASET_PATH),
                "--challenge-id",
                "easy-001",
                "--skip-judge",
            ],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        dirs = [path for path in tmp_path.iterdir() if path.is_dir()]
        assert len(dirs) == 1
        assert dirs[0].name.startswith("perfect-fake-agent_")
        assert (dirs[0] / "results.json").is_file()

    def test_explicit_output_dir_used_exactly(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "custom-results"
        result = run_enron_eval(output_dir=output_dir, extra_args=["--challenge-id", "easy-001"])

        assert result.returncode == 0, result.stderr
        assert (output_dir / "results.json").is_file()
        assert str(output_dir / "results.json") in result.stdout

    def test_dataset_version_recorded_from_manifest(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "results"
        result = run_enron_eval(output_dir=output_dir, extra_args=["--challenge-id", "easy-001"])

        assert result.returncode == 0, result.stderr
        payload = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
        assert payload["dataset_version"] == "0.1.0"
        assert "Dataset:  0.1.0" in result.stdout
