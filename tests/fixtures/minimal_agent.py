"""Minimal EnronAgent wired to the shared CLI for subprocess tests."""

from __future__ import annotations

import sys

from enron_challenge.cli import run_cli
from enron_challenge.models import IndexResult, StudentAgentSubmission


class MinimalAgent:
    @property
    def name(self) -> str:
        return "minimal-test-agent"

    def index(self, dataset_path: str, index_dir: str) -> IndexResult:
        print(f"indexing {dataset_path} -> {index_dir}", file=sys.stderr)
        return IndexResult(status="ok", stats={"indexed": True})

    def prompt(
        self,
        dataset_path: str,
        index_dir: str,
        challenge,
    ) -> StudentAgentSubmission:
        print(f"solving {challenge.id}", file=sys.stderr)
        return StudentAgentSubmission(
            challenge_id=challenge.id,
            answer="stub-answer",
            evidence_message_ids=["<stub@example.com>"],
        )


def main() -> None:
    run_cli(MinimalAgent())


if __name__ == "__main__":
    main()
