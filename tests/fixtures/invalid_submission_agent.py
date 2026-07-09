"""Fake agent that returns JSON missing required submission fields."""

from __future__ import annotations

import sys

from enron_challenge.cli import run_cli
from enron_challenge.models import IndexResult


class InvalidSubmissionAgent:
    @property
    def name(self) -> str:
        return "invalid-submission-agent"

    def index(self, dataset_path: str, index_dir: str) -> IndexResult:
        return IndexResult(status="ok")

    def prompt(self, dataset_path: str, index_dir: str, challenge) -> dict:
        print(f"invalid submission on {challenge.id}", file=sys.stderr)
        return {"answer": "missing fields"}


def main() -> None:
    run_cli(InvalidSubmissionAgent())


if __name__ == "__main__":
    main()
