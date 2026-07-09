"""Subprocess tests for the Eval Runner with a perfect fake agent."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "student_dataset"
PERFECT_AGENT = PROJECT_ROOT / "tests" / "fixtures" / "perfect_agent.py"


def run_enron_eval(output_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "enron_eval.cli",
            "--agent-cmd",
            sys.executable,
            str(PERFECT_AGENT),
            "--dataset",
            str(DATASET_PATH),
            "--output-dir",
            str(output_dir),
            "--skip-judge",
        ],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )


class TestEvalRunner:
    def test_perfect_agent_scores_full_points(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "results"
        result = run_enron_eval(output_dir)

        assert result.returncode == 0, result.stderr

        json_path = output_dir / "results.json"
        md_path = output_dir / "results.md"
        assert json_path.is_file()
        assert md_path.is_file()

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert payload["agent_name"] == "perfect-fake-agent"
        assert payload["dataset_version"] == "0.1.0"
        assert payload["started_at"]
        assert payload["finished_at"]
        assert payload["duration_seconds"] >= 0
        assert payload["max_points"] == 142
        assert payload["total_points"] == 142
        assert len(payload["challenges"]) == 28

        for challenge in payload["challenges"]:
            assert challenge["status"] == "correct"
            assert challenge["points_earned"] == challenge["max_points"]
            assert challenge["duration_seconds"] >= 0
            assert challenge["grading"]["answer_match"] is True
            assert challenge["grading"]["evidence_pass"] is True

    def test_terminal_summary_includes_required_fields(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "results"
        result = run_enron_eval(output_dir)

        assert result.returncode == 0
        stdout = result.stdout
        assert "Eval complete" in stdout
        assert "Agent:    perfect-fake-agent" in stdout
        assert "Dataset:  0.1.0" in stdout
        assert "Score:    142/142" in stdout
        assert "JSON:" in stdout
        assert "MD:" in stdout
        assert str(output_dir / "results.json") in stdout
        assert str(output_dir / "results.md") in stdout
        assert "easy-001" in stdout
        assert "Answer  Evidence  Judge" in stdout

    def test_fresh_index_directory_each_run(self, tmp_path: Path) -> None:
        output_dir_a = tmp_path / "run-a"
        output_dir_b = tmp_path / "run-b"

        result_a = run_enron_eval(output_dir_a)
        result_b = run_enron_eval(output_dir_b)

        assert result_a.returncode == 0
        assert result_b.returncode == 0

        index_dir_a = json.loads(
            (output_dir_a / "results.json").read_text(encoding="utf-8")
        )["index_dir"]
        index_dir_b = json.loads(
            (output_dir_b / "results.json").read_text(encoding="utf-8")
        )["index_dir"]

        assert index_dir_a
        assert index_dir_b
        assert index_dir_a != index_dir_b
        assert not Path(index_dir_a).exists()
        assert not Path(index_dir_b).exists()

    def test_markdown_results_contain_summary(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "results"
        result = run_enron_eval(output_dir)

        assert result.returncode == 0
        md = (output_dir / "results.md").read_text(encoding="utf-8")
        assert "# Eval Results" in md
        assert "perfect-fake-agent" in md
        assert "142/142" in md
        assert "easy-001" in md
