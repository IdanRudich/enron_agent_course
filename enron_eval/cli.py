"""CLI entry point for the Eval Runner."""

from __future__ import annotations

import argparse
import sys

from enron_eval.runner import ChallengeSelector, EvalRunnerError, run_eval


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate a Student Agent CLI against the Golden Set",
    )
    parser.add_argument(
        "--agent-cmd",
        nargs="+",
        required=True,
        help="Agent CLI command prefix (e.g. python my_agent.py)",
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to the packaged dataset directory",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for results.json and results.md (default: slugified agent name + timestamp)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Subprocess timeout in seconds for agent commands",
    )

    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--all",
        action="store_true",
        help="Run all challenges (default when no selector is provided)",
    )
    selection.add_argument(
        "--challenge-id",
        action="append",
        dest="challenge_ids",
        metavar="ID",
        help="Run one challenge id (repeatable)",
    )
    selection.add_argument(
        "--difficulty",
        action="append",
        dest="difficulties",
        choices=["easy", "medium", "hard"],
        metavar="LEVEL",
        help="Run challenges for one difficulty (repeatable)",
    )
    parser.add_argument(
        "--skip-judge",
        action="store_true",
        help="Skip answer-equivalence judge (for testing without judge credentials)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    selector = ChallengeSelector(
        select_all=args.all,
        challenge_ids=args.challenge_ids,
        difficulties=args.difficulties,
    )

    try:
        run_eval(
            agent_cmd=args.agent_cmd,
            dataset_path=args.dataset,
            output_dir=args.output_dir,
            selector=selector,
            timeout=args.timeout,
            skip_judge=args.skip_judge,
        )
    except EvalRunnerError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
