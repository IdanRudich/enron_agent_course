"""Tests for .env loading and smoke env validation."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from enron_eval.env_loader import load_dotenv, prepare_smoke_env, require_vars


class TestEnvLoader:
    def test_load_dotenv_does_not_override_existing(self, tmp_path: Path, monkeypatch) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text(
            "ENRON_AGENT_API_KEY=file-key\n"
            "ENRON_AGENT_MODEL=MiniMax-M3\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("ENRON_AGENT_API_KEY", "existing-key")
        monkeypatch.delenv("ENRON_AGENT_MODEL", raising=False)

        load_dotenv(env_file)

        assert os.environ["ENRON_AGENT_API_KEY"] == "existing-key"
        assert os.environ["ENRON_AGENT_MODEL"] == "MiniMax-M3"

    def test_require_vars_exits_when_missing(self, monkeypatch) -> None:
        monkeypatch.delenv("ENRON_AGENT_API_KEY", raising=False)
        with pytest.raises(SystemExit):
            require_vars(("ENRON_AGENT_API_KEY",))

    def test_prepare_smoke_env_applies_defaults(self, tmp_path: Path, monkeypatch) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text(
            "ENRON_AGENT_API_KEY=agent-key\n"
            "ENRON_AGENT_MODEL=MiniMax-M3\n"
            "ENRON_JUDGE_API_KEY=judge-key\n"
            "ENRON_JUDGE_MODEL=MiniMax-M3\n",
            encoding="utf-8",
        )
        monkeypatch.delenv("ENRON_AGENT_BASE_URL", raising=False)
        monkeypatch.delenv("ENRON_JUDGE_BASE_URL", raising=False)

        prepare_smoke_env(env_file)

        assert os.environ["ENRON_AGENT_BASE_URL"] == "https://api.minimax.io/v1"
        assert os.environ["ENRON_JUDGE_BASE_URL"] == "https://api.minimax.io/v1"
