"""Load .env files and validate Minimax credentials for manual smoke runs."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from enron_eval.judge import DEFAULT_JUDGE_BASE_URL

REQUIRED_AGENT_VARS = ("ENRON_AGENT_API_KEY", "ENRON_AGENT_MODEL")
REQUIRED_JUDGE_VARS = ("ENRON_JUDGE_API_KEY", "ENRON_JUDGE_MODEL")


def load_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE pairs from a .env file without overriding existing env vars."""
    env_path = path if path is not None else Path.cwd() / ".env"
    if not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)


def ensure_minimax_defaults() -> None:
    """Apply default Minimax base URLs when unset."""
    os.environ.setdefault("ENRON_AGENT_BASE_URL", DEFAULT_JUDGE_BASE_URL)
    os.environ.setdefault("ENRON_JUDGE_BASE_URL", DEFAULT_JUDGE_BASE_URL)


def require_vars(names: tuple[str, ...]) -> None:
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        print(f"Missing required env var(s): {', '.join(missing)}", file=sys.stderr)
        raise SystemExit(1)


def prepare_smoke_env(dotenv_path: Path | None = None) -> None:
    """Load .env, apply defaults, and validate agent + judge credentials."""
    load_dotenv(dotenv_path)
    ensure_minimax_defaults()
    require_vars(REQUIRED_AGENT_VARS)
    require_vars(REQUIRED_JUDGE_VARS)
