"""CLI entry point for the reference solution agent."""

from __future__ import annotations

from enron_challenge.cli import run_cli

from enron_reference.agent import ReferenceAgent


def main() -> None:
    run_cli(ReferenceAgent())


if __name__ == "__main__":
    main()
