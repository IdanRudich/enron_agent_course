"""Fake agents that trigger protocol errors for CLI adapter tests."""

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
        return "not valid json {{{"


class InvalidSubmissionAgent:
    @property
    def name(self) -> str:
        return "invalid-submission-agent"

    def index(self, dataset_path: str, index_dir: str) -> IndexResult:
        return IndexResult(status="ok")

    def prompt(self, dataset_path: str, index_dir: str, challenge) -> dict:
        return {"answer": "missing fields"}


class CrashAgent:
    @property
    def name(self) -> str:
        return "crash-agent"

    def index(self, dataset_path: str, index_dir: str) -> IndexResult:
        return IndexResult(status="ok")

    def prompt(self, dataset_path: str, index_dir: str, challenge) -> None:
        raise RuntimeError("agent crashed during prompt")


_AGENTS = {
    "invalid-json": InvalidJsonAgent,
    "invalid-submission": InvalidSubmissionAgent,
    "crash": CrashAgent,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in _AGENTS:
        print(
            f"usage: {sys.argv[0]} <{'|'.join(_AGENTS)}> <cli-args...>",
            file=sys.stderr,
        )
        sys.exit(1)
    agent_kind = sys.argv.pop(1)
    run_cli(_AGENTS[agent_kind]())


if __name__ == "__main__":
    main()
