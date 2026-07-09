"""Fake agent whose metadata command fails."""

from __future__ import annotations

import sys


def main() -> None:
    print("metadata unavailable", file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
