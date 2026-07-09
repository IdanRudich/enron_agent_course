"""Fake agent that fails during index."""

from __future__ import annotations

import sys

from enron_challenge.cli import run_cli


class IndexFailAgent:
    @property
    def name(self) -> str:
        return "index-fail-agent"

    def index(self, dataset_path: str, index_dir: str) -> None:
        print("index failed", file=sys.stderr)
        raise RuntimeError("index build failed")

    def prompt(self, dataset_path: str, index_dir: str, challenge) -> None:
        raise RuntimeError("prompt should not run")


def main() -> None:
    run_cli(IndexFailAgent())


if __name__ == "__main__":
    main()
