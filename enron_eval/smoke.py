"""Manual Minimax smoke path for the reference agent and judge."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from enron_eval.agent_cli import run_index, run_metadata, run_prompt
from enron_eval.env_loader import prepare_smoke_env
from enron_eval.runner import ChallengeSelector, EvalRunnerError, build_agent_subprocess_env, run_eval

DEFAULT_DATASET = "student_dataset"
PROMPT_PREVIEW_CHARS = 500


def _resolve_reference_cmd() -> list[str]:
    return [sys.executable, "-m", "enron_reference.cli"]


def _default_output_dir(label: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path(f"/tmp/enron-smoke-{stamp}-{label}")


def _phase_selector(phase: str) -> ChallengeSelector:
    if phase == "single":
        return ChallengeSelector(challenge_ids=["easy-001"])
    if phase == "easy":
        return ChallengeSelector(difficulties=["easy"])
    if phase == "full":
        return ChallengeSelector(select_all=True)
    raise ValueError(f"Unknown phase: {phase}")


def _log_section(title: str) -> None:
    print(f"\n=== {title} ===", file=sys.stderr)


def run_smoke(
    phase: str = "single",
    *,
    dataset: str | Path = DEFAULT_DATASET,
    output_dir: Path | None = None,
    dotenv_path: Path | None = None,
) -> None:
    prepare_smoke_env(dotenv_path)

    dataset_path = Path(dataset)
    agent_cmd = _resolve_reference_cmd()
    agent_env = build_agent_subprocess_env()
    label = phase if phase != "single" else "single"
    out_dir = output_dir or _default_output_dir(label)

    _log_section("metadata")
    metadata = run_metadata(agent_cmd, env=agent_env)
    if metadata.returncode != 0 or metadata.payload is None:
        raise SystemExit(
            f"metadata failed (exit {metadata.returncode}): {metadata.stderr.strip()}"
        )
    print(metadata.stdout, end="")

    _log_section("index")
    index_dir = out_dir.parent / f"{out_dir.name}-index"
    index_dir.mkdir(parents=True, exist_ok=True)
    index_result = run_index(
        agent_cmd,
        str(dataset_path),
        str(index_dir),
        env=agent_env,
    )
    if index_result.returncode != 0 or index_result.payload is None:
        raise SystemExit(
            f"index failed (exit {index_result.returncode}): {index_result.stderr.strip()}"
        )
    indexed = index_result.payload.get("indexed_messages", "?")
    print(f"indexed_messages: {indexed}", file=sys.stderr)

    _log_section("single prompt (easy-001)")
    prompt_result = run_prompt(
        agent_cmd,
        str(dataset_path),
        str(index_dir),
        "easy-001",
        env=agent_env,
    )
    if prompt_result.returncode != 0 or prompt_result.payload is None:
        raise SystemExit(
            f"prompt failed (exit {prompt_result.returncode}): {prompt_result.stderr.strip()}"
        )
    preview = prompt_result.stdout[:PROMPT_PREVIEW_CHARS]
    if len(prompt_result.stdout) > PROMPT_PREVIEW_CHARS:
        preview += "..."
    print(preview, file=sys.stderr)

    _log_section(f"enron-eval: {label} -> {out_dir}")
    try:
        run_eval(
            agent_cmd=agent_cmd,
            dataset_path=dataset_path,
            output_dir=out_dir,
            selector=_phase_selector(phase),
            verbose=True,
        )
    except EvalRunnerError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    _log_section("done")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the manual Minimax smoke path for enron-reference + judge. "
            "Loads .env from the current directory when present."
        ),
    )
    parser.add_argument(
        "phase",
        nargs="?",
        default="single",
        choices=["single", "easy", "full"],
        help="single: easy-001 only (default); easy: all easy; full: all 28 challenges",
    )
    parser.add_argument(
        "--dataset",
        default=DEFAULT_DATASET,
        help=f"Dataset directory (default: {DEFAULT_DATASET})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Results directory (default: /tmp/enron-smoke-<timestamp>-<phase>)",
    )
    parser.add_argument(
        "--dotenv",
        type=Path,
        default=None,
        help="Path to .env file (default: ./.env when present)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    run_smoke(
        args.phase,
        dataset=args.dataset,
        output_dir=args.output_dir,
        dotenv_path=args.dotenv,
    )


if __name__ == "__main__":
    main()
