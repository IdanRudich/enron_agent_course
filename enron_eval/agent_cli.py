"""Invoke a Student Agent CLI through subprocesses."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from enron_challenge.models import AgentMetadata, IndexResult, StudentAgentSubmission


@dataclass(frozen=True)
class AgentCommandResult:
    returncode: int
    stdout: str
    stderr: str
    payload: dict[str, Any] | None = None
    timed_out: bool = False


def run_metadata(
    agent_cmd: list[str],
    *,
    timeout: float | None = None,
    env: dict[str, str] | None = None,
) -> AgentCommandResult:
    return _run_json_command(agent_cmd + ["metadata"], AgentMetadata, timeout=timeout, env=env)


def run_index(
    agent_cmd: list[str],
    dataset_path: str,
    index_dir: str,
    *,
    timeout: float | None = None,
    env: dict[str, str] | None = None,
) -> AgentCommandResult:
    return _run_json_command(
        agent_cmd + ["index", dataset_path, index_dir],
        IndexResult,
        timeout=timeout,
        env=env,
    )


def run_prompt(
    agent_cmd: list[str],
    dataset_path: str,
    index_dir: str,
    challenge_id: str,
    *,
    timeout: float | None = None,
    env: dict[str, str] | None = None,
) -> AgentCommandResult:
    return _run_json_command(
        agent_cmd + ["prompt", dataset_path, index_dir, challenge_id],
        StudentAgentSubmission,
        timeout=timeout,
        env=env,
    )


def _run_json_command(
    command: list[str],
    model_type: type,
    *,
    timeout: float | None = None,
    env: dict[str, str] | None = None,
) -> AgentCommandResult:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env if env is not None else os.environ,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode()
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode()
        return AgentCommandResult(
            returncode=-1,
            stdout=stdout,
            stderr=stderr,
            payload=None,
            timed_out=True,
        )

    payload = None
    if completed.stdout.strip():
        try:
            payload = json.loads(completed.stdout)
            model_type.model_validate(payload)
        except (json.JSONDecodeError, ValidationError):
            payload = None

    return AgentCommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        payload=payload,
    )
