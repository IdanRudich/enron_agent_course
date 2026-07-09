"""Fake agent that returns invalid JSON on prompt."""

from __future__ import annotations

import sys

from enron_challenge.cli import run_cli
from enron_challenge.models import IndexResult


class InvalidJsonAgent:
    @property
    def name(self) -> str:
        return "invalid-json-agent"

    def index(self, dataset_path: str, index_dir: str) -> IndexResult:
        return IndexResult(status="ok")

    def prompt(self, dataset_path: str, index_dir: str, challenge) -> str:
        print(f"invalid json on {challenge.id}", file=sys.stderr)
        print("not valid json {{{")
        raise SystemExit(0)


def main() -> None:
    run_cli(InvalidJsonAgent())


if __name__ == "__main__":
    main()
