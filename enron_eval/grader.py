"""Deterministic grader for Golden Answer scoring."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from enron_challenge.models import StudentAgentSubmission
from enron_eval.mail_index import (
    MailIndex,
    build_mail_index,
    normalize_message_id,
    predicate_matches_row,
    rows_matching_prompt_bounds,
)
from enron_eval.judge import AnswerEquivalenceJudge, JudgeInput
from enron_eval.models import AcceptedAnswer, GoldenAnswer, GradingDetail


def grade_submission(
    submission: StudentAgentSubmission,
    golden: GoldenAnswer,
    max_points: int,
    *,
    mail_index: MailIndex | None = None,
    dataset_path: str | Path | None = None,
    challenge_prompt: str | None = None,
    challenge_difficulty: str | None = None,
    expected_answer_format: str | None = None,
    judge: AnswerEquivalenceJudge | None = None,
) -> tuple[int, GradingDetail]:
    """Return points earned and grading detail for one submission."""
    answer_match = _answer_matches(submission.answer, golden.accepted_answer)
    evidence_pass = _evidence_passes(
        submission.evidence_message_ids,
        golden,
        mail_index=mail_index,
        dataset_path=dataset_path,
        challenge_prompt=challenge_prompt,
        challenge_difficulty=challenge_difficulty,
    )

    judge_used = False
    judge_equivalent: bool | None = None
    judge_rationale: str | None = None

    if evidence_pass and not answer_match and judge is not None:
        judge_used = True
        verdict = judge.evaluate(
            JudgeInput(
                challenge_prompt=challenge_prompt or "",
                expected_answer_value=golden.accepted_answer.value,
                aliases=list(golden.accepted_answer.aliases),
                expected_answer_format=expected_answer_format or "",
                student_answer=submission.answer,
            )
        )
        judge_equivalent = verdict.equivalent
        judge_rationale = verdict.rationale
        if verdict.equivalent:
            answer_match = True

    points = max_points if answer_match and evidence_pass else 0
    detail = GradingDetail(
        answer_match=answer_match,
        evidence_pass=evidence_pass,
        evidence_mode=golden.evidence_mode,
        judge_used=judge_used,
        judge_equivalent=judge_equivalent,
        judge_rationale=judge_rationale,
    )
    return points, detail


def _answer_matches(answer: Any, accepted: AcceptedAnswer) -> bool:
    if _values_equivalent(answer, accepted.value):
        return True
    return any(_values_equivalent(answer, alias) for alias in accepted.aliases)


def _values_equivalent(left: Any, right: Any) -> bool:
    if isinstance(left, list) and isinstance(right, list):
        return _normalize_answer_set(left) == _normalize_answer_set(right)
    return left == right


def _normalize_answer_set(values: list[Any]) -> frozenset[Any]:
    normalized: set[Any] = set()
    for value in values:
        if isinstance(value, str):
            normalized.add(value.strip().lower())
        else:
            normalized.add(value)
    return frozenset(normalized)


def _evidence_passes(
    submitted_ids: list[str],
    golden: GoldenAnswer,
    *,
    mail_index: MailIndex | None,
    dataset_path: str | Path | None,
    challenge_prompt: str | None,
    challenge_difficulty: str | None,
) -> bool:
    if not submitted_ids:
        return False

    normalized_ids = [_normalize_submitted_id(message_id) for message_id in submitted_ids]
    normalized_ids = [message_id for message_id in normalized_ids if message_id is not None]
    if not normalized_ids:
        return False

    if golden.evidence_mode == "all":
        required = set(golden.evidence_message_ids)
        return required.issubset(set(normalized_ids))

    if golden.evidence_mode == "any":
        required = set(golden.evidence_message_ids)
        return bool(required.intersection(normalized_ids))

    if golden.evidence_mode == "predicate":
        return _predicate_evidence_passes(
            normalized_ids,
            golden,
            mail_index=mail_index,
            dataset_path=dataset_path,
            challenge_prompt=challenge_prompt,
            challenge_difficulty=challenge_difficulty,
        )

    return False


def _normalize_submitted_id(message_id: str) -> str | None:
    return normalize_message_id(message_id)


def _predicate_evidence_passes(
    submitted_ids: list[str],
    golden: GoldenAnswer,
    *,
    mail_index: MailIndex | None,
    dataset_path: str | Path | None,
    challenge_prompt: str | None,
    challenge_difficulty: str | None,
) -> bool:
    predicate = golden.evidence_predicate
    if not predicate:
        return False

    index = mail_index
    if index is None:
        if dataset_path is None:
            return False
        index = build_mail_index(str(dataset_path))

    prompt = challenge_prompt or ""
    difficulty = challenge_difficulty or ""

    for message_id in submitted_ids:
        rows = rows_matching_prompt_bounds(
            message_id,
            difficulty=difficulty,
            prompt=prompt,
            mail_index=index,
        )
        if any(predicate_matches_row(predicate, row) for row in rows):
            return True
    return False
