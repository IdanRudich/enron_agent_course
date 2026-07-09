"""Fake agent that crashes during prompt."""

from __future__ import annotations

import sys

from enron_challenge.cli import run_cli
from enron_challenge.models import IndexResult


class CrashAgent:
    @property
    def name(self) -> str:
        return "crash-agent"

    def index(self, dataset_path: str, index_dir: str) -> IndexResult:
        print(f"indexing {dataset_path} -> {index_dir}", file=sys.stderr)
        return IndexResult(status="ok", stats={"indexed": True})

    def prompt(self, dataset_path: str, index_dir: str, challenge) -> None:
        print(f"crashing on {challenge.id}", file=sys.stderr)
        raise RuntimeError("agent crashed during prompt")


def main() -> None:
    run_cli(CrashAgent())


if __name__ == "__main__":
    main()
