"""Fake agent that sleeps through prompt timeouts."""

from __future__ import annotations

import sys
import time

from enron_challenge.cli import run_cli
from enron_challenge.models import IndexResult


class TimeoutAgent:
    @property
    def name(self) -> str:
        return "timeout-agent"

    def index(self, dataset_path: str, index_dir: str) -> IndexResult:
        print(f"indexing {dataset_path} -> {index_dir}", file=sys.stderr)
        return IndexResult(status="ok", stats={"indexed": True})

    def prompt(self, dataset_path: str, index_dir: str, challenge) -> None:
        print(f"sleeping on {challenge.id}", file=sys.stderr)
        time.sleep(3600)


def main() -> None:
    run_cli(TimeoutAgent())


if __name__ == "__main__":
    main()
