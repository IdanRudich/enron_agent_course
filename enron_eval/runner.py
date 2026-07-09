"""Eval Runner: subprocess agent evaluation with grading and result output."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from enron_challenge.models import StudentAgentSubmission
from enron_eval.agent_cli import AgentCommandResult, run_index, run_metadata, run_prompt
from enron_eval.dataset import load_dataset_version, load_golden_challenges
from enron_eval.grader import grade_submission
from enron_eval.judge import (
    JUDGE_ENV_VARS,
    AnswerEquivalenceJudge,
    JudgeConfigError,
    JudgeError,
    load_judge_config,
)
from enron_eval.mail_index import MailIndex, build_mail_index
from enron_eval.models import ChallengeResult, EvalRunResult, GoldenChallengeRecord
from enron_eval.results import print_terminal_summary, write_results


class EvalRunnerError(Exception):
    """Fatal eval runner failure (metadata, index, or selector)."""


@dataclass(frozen=True)
class ChallengeSelector:
    select_all: bool = False
    challenge_ids: list[str] | None = None
    difficulties: list[str] | None = None


def run_eval(
    agent_cmd: list[str],
    dataset_path: str | Path,
    output_dir: str | Path | None = None,
    *,
    selector: ChallengeSelector | None = None,
    timeout: float | None = None,
    skip_judge: bool = False,
    verbose: bool = False,
) -> EvalRunResult:
    dataset_path = Path(dataset_path)
    all_challenges = load_golden_challenges(dataset_path)
    dataset_version = load_dataset_version(dataset_path)
    selector = selector or ChallengeSelector()

    judge: AnswerEquivalenceJudge | None = None
    if not skip_judge:
        try:
            judge = AnswerEquivalenceJudge.from_config(load_judge_config())
        except JudgeConfigError as exc:
            raise EvalRunnerError(str(exc)) from exc

    agent_env = build_agent_subprocess_env()

    started_at = _utc_now()
    run_start = perf_counter()

    _log(verbose, "Running agent metadata...")
    metadata_result = run_metadata(agent_cmd, timeout=timeout, env=agent_env)
    if metadata_result.timed_out:
        raise EvalRunnerError("Agent metadata timed out")
    if metadata_result.returncode != 0 or metadata_result.payload is None:
        raise EvalRunnerError(
            f"Agent metadata failed (exit {metadata_result.returncode}): "
            f"{metadata_result.stderr.strip()}"
        )
    agent_name = metadata_result.payload["agent_name"]
    if not agent_name:
        raise EvalRunnerError("Agent metadata failed: missing agent_name")
    _log(verbose, f"Agent: {agent_name}")

    selected_challenges = _resolve_challenges(all_challenges, selector)
    total = len(selected_challenges)
    _log(verbose, f"Selected {total} challenge(s)")

    if output_dir is None:
        output_dir = _default_output_dir(agent_name)
    else:
        output_dir = Path(output_dir)

    with tempfile.TemporaryDirectory(prefix="enron-index-") as index_dir:
        _log(verbose, "Building agent index...")
        index_result = run_index(
            agent_cmd,
            str(dataset_path),
            index_dir,
            timeout=timeout,
            env=agent_env,
        )
        if index_result.timed_out:
            raise EvalRunnerError("Agent index timed out")
        if index_result.returncode != 0 or index_result.payload is None:
            raise EvalRunnerError(
                f"Agent index failed (exit {index_result.returncode}): "
                f"{index_result.stderr.strip()}"
            )
        indexed = index_result.payload.get("indexed_messages", "?")
        _log(verbose, f"Index ready ({indexed} messages)")

        mail_index = build_mail_index(str(dataset_path))
        challenge_results: list[ChallengeResult] = []
        for index, challenge in enumerate(selected_challenges, start=1):
            _log(verbose, f"[{index}/{total}] {challenge.id} ({challenge.difficulty})...")
            try:
                challenge_result = _evaluate_challenge(
                    agent_cmd,
                    dataset_path,
                    index_dir,
                    challenge,
                    mail_index=mail_index,
                    timeout=timeout,
                    agent_env=agent_env,
                    judge=judge,
                )
            except JudgeError as exc:
                raise EvalRunnerError(str(exc)) from exc
            challenge_results.append(challenge_result)
            _log(
                verbose,
                f"  -> {challenge_result.status} "
                f"({challenge_result.points_earned}/{challenge_result.max_points}) "
                f"in {challenge_result.duration_seconds:.1f}s",
            )

        finished_at = _utc_now()
        total_duration = perf_counter() - run_start
        max_points = sum(c.max_points for c in challenge_results)
        total_points = sum(c.points_earned for c in challenge_results)

        result = EvalRunResult(
            agent_name=agent_name,
            dataset_version=dataset_version,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=total_duration,
            total_points=total_points,
            max_points=max_points,
            index_dir=index_dir,
            challenges=challenge_results,
        )

        json_path, md_path = write_results(result, output_dir)
        print_terminal_summary(result, json_path, md_path)
        return result


def build_agent_subprocess_env(
    base_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Return subprocess env with judge credentials removed."""
    env = dict(base_env or os.environ)
    for key in JUDGE_ENV_VARS:
        env.pop(key, None)
    return env


def _evaluate_challenge(
    agent_cmd: list[str],
    dataset_path: Path,
    index_dir: str,
    challenge: GoldenChallengeRecord,
    *,
    mail_index: MailIndex,
    timeout: float | None,
    agent_env: dict[str, str],
    judge: AnswerEquivalenceJudge | None,
) -> ChallengeResult:
    challenge_start = perf_counter()
    prompt_result = run_prompt(
        agent_cmd,
        str(dataset_path),
        index_dir,
        challenge.id,
        timeout=timeout,
        env=agent_env,
    )
    duration = perf_counter() - challenge_start

    if _is_prompt_failure(prompt_result):
        failure_kind = _classify_prompt_failure(prompt_result)
        raw_stdout = _raw_stdout_for_failure(prompt_result)
        return ChallengeResult(
            challenge_id=challenge.id,
            difficulty=challenge.difficulty,
            max_points=challenge.points,
            points_earned=0,
            status=failure_kind,
            duration_seconds=duration,
            stderr=prompt_result.stderr,
            failure_kind=failure_kind,
            raw_stdout=raw_stdout,
        )

    submission = StudentAgentSubmission.model_validate(prompt_result.payload)
    expected_format = str(challenge.expected_submission.get("answer_format", ""))
    points, grading = grade_submission(
        submission,
        challenge.golden_answer,
        challenge.points,
        mail_index=mail_index,
        challenge_prompt=challenge.prompt,
        challenge_difficulty=challenge.difficulty,
        expected_answer_format=expected_format,
        judge=judge,
    )
    status = "correct" if points == challenge.points else "incorrect"

    return ChallengeResult(
        challenge_id=challenge.id,
        difficulty=challenge.difficulty,
        max_points=challenge.points,
        points_earned=points,
        status=status,
        duration_seconds=duration,
        submission=submission.model_dump(mode="json"),
        grading=grading,
        stderr=prompt_result.stderr,
    )


def _resolve_challenges(
    all_challenges: list[GoldenChallengeRecord],
    selector: ChallengeSelector,
) -> list[GoldenChallengeRecord]:
    if selector.challenge_ids is not None:
        by_id = {challenge.id: challenge for challenge in all_challenges}
        selected: list[GoldenChallengeRecord] = []
        for challenge_id in selector.challenge_ids:
            if challenge_id not in by_id:
                raise EvalRunnerError(f"Unknown challenge id: {challenge_id}")
            selected.append(by_id[challenge_id])
        return selected

    if selector.difficulties is not None:
        allowed = set(selector.difficulties)
        selected = [c for c in all_challenges if c.difficulty in allowed]
        if not selected:
            raise EvalRunnerError(
                f"No challenges match difficulty selector: {', '.join(selector.difficulties)}"
            )
        return selected

    return list(all_challenges)


def _is_prompt_failure(result: AgentCommandResult) -> bool:
    return result.timed_out or result.returncode != 0 or result.payload is None


def _classify_prompt_failure(result: AgentCommandResult) -> str:
    if result.timed_out:
        return "timeout"
    if result.returncode == 2:
        return "invalid_json"
    if result.returncode == 3:
        return "invalid_submission"
    if result.returncode != 0:
        return "crash"
    if result.stdout.strip():
        try:
            json.loads(result.stdout)
        except json.JSONDecodeError:
            return "invalid_json"
    return "invalid_submission"


def _raw_stdout_for_failure(result: AgentCommandResult) -> str | None:
    if result.payload is not None:
        return None
    stdout = result.stdout
    return stdout if stdout else None


def _default_output_dir(agent_name: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = _slugify(agent_name)
    return Path.cwd() / f"{slug}_{timestamp}"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "agent"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _log(verbose: bool, message: str) -> None:
    if verbose:
        print(message, file=sys.stderr)
