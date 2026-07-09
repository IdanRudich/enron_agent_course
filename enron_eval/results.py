"""Write eval run results as JSON and Markdown."""

from __future__ import annotations

import json
from pathlib import Path

from enron_eval.models import ChallengeResult, EvalRunResult


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


def print_terminal_summary(
    result: EvalRunResult,
    json_path: Path,
    md_path: Path,
) -> None:
    pct = (100 * result.total_points / result.max_points) if result.max_points else 0.0

    print()
    print("Eval complete")
    print(f"  Agent:    {result.agent_name}")
    print(f"  Dataset:  {result.dataset_version}")
    print(f"  Duration: {result.duration_seconds:.1f}s")
    print(f"  Score:    {result.total_points}/{result.max_points} ({pct:.0f}%)")
    print()
    print("  Challenge       Diff   Score  Status       Answer  Evidence  Judge   Time")
    print(f"  {'-' * 78}")
    for challenge in result.challenges:
        answer_col, evidence_col, judge_col = _grading_columns(challenge)
        print(
            f"  {challenge.challenge_id:<15} "
            f"{challenge.difficulty:<6} "
            f"{challenge.points_earned}/{challenge.max_points:<4} "
            f"{challenge.status:<12} "
            f"{answer_col:<7} "
            f"{evidence_col:<9} "
            f"{judge_col:<7} "
            f"{challenge.duration_seconds:.1f}s"
        )
    print()
    print(f"  JSON: {json_path}")
    print(f"  MD:   {md_path}")


def _grading_columns(challenge: ChallengeResult) -> tuple[str, str, str]:
    if challenge.grading is None:
        return "—", "—", challenge.failure_kind or "—"

    grading = challenge.grading
    answer_col = "yes" if grading.answer_match else "no"
    evidence_col = "yes" if grading.evidence_pass else "no"
    if grading.judge_used:
        judge_col = "equiv" if grading.judge_equivalent else "reject"
    else:
        judge_col = "—"
    return answer_col, evidence_col, judge_col
