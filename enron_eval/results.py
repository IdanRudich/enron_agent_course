"""Write eval run results as JSON and Markdown."""

from __future__ import annotations

import json
from pathlib import Path

from enron_eval.models import EvalRunResult


def write_results(result: EvalRunResult, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "results.json"
    md_path = output_dir / "results.md"

    json_path.write_text(
        result.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(_render_markdown(result), encoding="utf-8")
    return json_path, md_path


def _render_markdown(result: EvalRunResult) -> str:
    lines = [
        "# Eval Results",
        "",
        f"- **Agent:** {result.agent_name}",
        f"- **Dataset version:** {result.dataset_version}",
        f"- **Started:** {result.started_at}",
        f"- **Finished:** {result.finished_at}",
        f"- **Duration:** {result.duration_seconds:.2f}s",
        f"- **Score:** {result.total_points}/{result.max_points}",
        "",
        "## Challenges",
        "",
        "| Challenge | Difficulty | Points | Status | Duration |",
        "| --- | --- | --- | --- | --- |",
    ]
    for challenge in result.challenges:
        lines.append(
            f"| {challenge.challenge_id} | {challenge.difficulty} | "
            f"{challenge.points_earned}/{challenge.max_points} | "
            f"{challenge.status} | {challenge.duration_seconds:.2f}s |"
        )
    lines.append("")
    return "\n".join(lines)


def print_terminal_summary(result: EvalRunResult, json_path: Path) -> None:
    print(f"Agent: {result.agent_name}")
    print(f"Dataset: {result.dataset_version}")
    print(f"Score: {result.total_points}/{result.max_points}")
    print(f"Results: {json_path}")
