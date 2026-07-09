"""Unit tests for deterministic Golden Answer grading."""

from __future__ import annotations

from pathlib import Path

import pytest

from enron_challenge.models import StudentAgentSubmission
from enron_eval.grader import grade_submission
from enron_eval.mail_index import build_mail_index
from enron_eval.models import AcceptedAnswer, GoldenAnswer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "student_dataset"


@pytest.fixture(scope="module")
def mail_index():
    return build_mail_index(str(DATASET_PATH))


def _submission(
    *,
    challenge_id: str = "test-001",
    answer,
    evidence_message_ids: list[str],
    **extra,
) -> StudentAgentSubmission:
    return StudentAgentSubmission(
        challenge_id=challenge_id,
        answer=answer,
        evidence_message_ids=evidence_message_ids,
        **extra,
    )


def _golden(
    *,
    value,
    aliases: list | None = None,
    evidence_message_ids: list[str],
    evidence_mode: str = "all",
    evidence_predicate: dict | None = None,
) -> GoldenAnswer:
    return GoldenAnswer(
        accepted_answer=AcceptedAnswer(value=value, aliases=aliases or []),
        evidence_message_ids=evidence_message_ids,
        evidence_mode=evidence_mode,
        evidence_predicate=evidence_predicate,
    )


class TestAnswerMatching:
    def test_canonical_scalar_match(self) -> None:
        golden = _golden(value="sender@example.com", evidence_message_ids=["<a@b>"])
        submission = _submission(answer="sender@example.com", evidence_message_ids=["<a@b>"])
        points, detail = grade_submission(submission, golden, 2)
        assert points == 2
        assert detail.answer_match is True

    def test_alias_scalar_match(self) -> None:
        golden = _golden(
            value=136,
            aliases=["136 emails"],
            evidence_message_ids=["<a@b>"],
        )
        submission = _submission(answer="136 emails", evidence_message_ids=["<a@b>"])
        points, detail = grade_submission(submission, golden, 5)
        assert points == 5
        assert detail.answer_match is True

    def test_integer_answer_match(self) -> None:
        golden = _golden(value=51, aliases=["51 emails"], evidence_message_ids=["<a@b>"])
        submission = _submission(answer=51, evidence_message_ids=["<a@b>"])
        points, detail = grade_submission(submission, golden, 5)
        assert points == 5
        assert detail.answer_match is True

    def test_set_answer_order_independent(self) -> None:
        addresses = [
            "bill.iii@enron.com",
            "cara.semperger@enron.com",
            "kourtney.nelson@enron.com",
        ]
        golden = _golden(value=addresses, evidence_message_ids=["<a@b>"])
        submission = _submission(
            answer=list(reversed(addresses)),
            evidence_message_ids=["<a@b>"],
        )
        points, detail = grade_submission(submission, golden, 5)
        assert points == 5
        assert detail.answer_match is True

    def test_set_answer_case_insensitive(self) -> None:
        golden = _golden(
            value=["bill.iii@enron.com", "cara.semperger@enron.com"],
            evidence_message_ids=["<a@b>"],
        )
        submission = _submission(
            answer=["Bill.III@enron.com", "CARA.SEMPERGER@enron.com"],
            evidence_message_ids=["<a@b>"],
        )
        points, detail = grade_submission(submission, golden, 5)
        assert points == 5
        assert detail.answer_match is True

    def test_wrong_answer_scores_zero(self) -> None:
        golden = _golden(value="correct", evidence_message_ids=["<a@b>"])
        submission = _submission(answer="wrong", evidence_message_ids=["<a@b>"])
        points, detail = grade_submission(submission, golden, 2)
        assert points == 0
        assert detail.answer_match is False


class TestEvidenceAllMode:
    def test_all_required_ids_present(self) -> None:
        golden = _golden(
            value="ok",
            evidence_message_ids=["<a@b>", "<c@d>"],
            evidence_mode="all",
        )
        submission = _submission(
            answer="ok",
            evidence_message_ids=["<a@b>", "<c@d>", "<extra@x>"],
        )
        points, detail = grade_submission(submission, golden, 3)
        assert points == 3
        assert detail.evidence_pass is True

    def test_all_mode_missing_id_fails(self) -> None:
        golden = _golden(
            value="ok",
            evidence_message_ids=["<a@b>", "<c@d>"],
            evidence_mode="all",
        )
        submission = _submission(answer="ok", evidence_message_ids=["<a@b>"])
        points, detail = grade_submission(submission, golden, 3)
        assert points == 0
        assert detail.evidence_pass is False

    def test_correct_answer_wrong_evidence_scores_zero(self) -> None:
        golden = _golden(value="ok", evidence_message_ids=["<a@b>"], evidence_mode="all")
        submission = _submission(answer="ok", evidence_message_ids=["<wrong@x>"])
        points, _detail = grade_submission(submission, golden, 3)
        assert points == 0


class TestEvidenceAnyMode:
    def test_any_one_listed_id_suffices(self) -> None:
        golden = _golden(
            value="ok",
            evidence_message_ids=["<a@b>", "<c@d>"],
            evidence_mode="any",
        )
        submission = _submission(answer="ok", evidence_message_ids=["<c@d>"])
        points, detail = grade_submission(submission, golden, 3)
        assert points == 3
        assert detail.evidence_pass is True

    def test_any_mode_no_listed_id_fails(self) -> None:
        golden = _golden(
            value="ok",
            evidence_message_ids=["<a@b>", "<c@d>"],
            evidence_mode="any",
        )
        submission = _submission(answer="ok", evidence_message_ids=["<other@x>"])
        points, detail = grade_submission(submission, golden, 3)
        assert points == 0
        assert detail.evidence_pass is False


class TestEvidencePredicateMode:
    def test_message_in_pack_predicate(self, mail_index) -> None:
        qualifying_id = "<28841806.1075841866914.JavaMail.evans@thyme>"
        golden = _golden(
            value=136,
            evidence_message_ids=[qualifying_id],
            evidence_mode="predicate",
            evidence_predicate={
                "type": "message_in_pack",
                "pack": "symes-k__power_marketer",
            },
        )
        submission = _submission(
            answer=136,
            evidence_message_ids=[qualifying_id],
        )
        points, detail = grade_submission(
            submission,
            golden,
            5,
            mail_index=mail_index,
            challenge_prompt="Count the Medium pack 'symes-k__power_marketer'.",
            challenge_difficulty="medium",
        )
        assert detail.evidence_pass is True
        assert points == 5

    def test_subject_prefix_predicate_qualifying_id(self, mail_index) -> None:
        qualifying_id = "<303482.1075855211200.JavaMail.evans@thyme>"
        golden = _golden(
            value=51,
            evidence_message_ids=[qualifying_id],
            evidence_mode="predicate",
            evidence_predicate={
                "type": "subject_prefix",
                "pack": "steffes-j__credit_issues",
                "subject_prefixes": ["re:", "fw:", "fwd:"],
                "trim_subject": True,
                "case_insensitive": True,
            },
        )
        submission = _submission(answer=51, evidence_message_ids=[qualifying_id])
        points, detail = grade_submission(
            submission,
            golden,
            5,
            mail_index=mail_index,
            challenge_prompt="Within the Medium pack 'steffes-j__credit_issues'.",
            challenge_difficulty="medium",
        )
        assert detail.evidence_pass is True
        assert points == 5

    def test_from_address_predicate_qualifying_id(self, mail_index) -> None:
        qualifying_id = "<30869027.1075846339788.JavaMail.evans@thyme>"
        golden = _golden(
            value=24,
            evidence_message_ids=[qualifying_id],
            evidence_mode="predicate",
            evidence_predicate={
                "type": "from_address",
                "pack": "kean-s__enrononline",
                "from_address": "leonardo.pacheco@enron.com",
                "case_insensitive": True,
            },
        )
        submission = _submission(answer=24, evidence_message_ids=[qualifying_id])
        points, detail = grade_submission(
            submission,
            golden,
            5,
            mail_index=mail_index,
            challenge_prompt="Within the Medium pack 'kean-s__enrononline'.",
            challenge_difficulty="medium",
        )
        assert detail.evidence_pass is True
        assert points == 5

    def test_address_in_headers_predicate_qualifying_id(self, mail_index) -> None:
        qualifying_id = "<16022517.1075839947691.JavaMail.evans@thyme>"
        golden = _golden(
            value=["chris.mallory@enron.com"],
            evidence_message_ids=[qualifying_id],
            evidence_mode="predicate",
            evidence_predicate={
                "type": "address_in_headers",
                "pack": "williams-w3__rt_strat",
                "roles": ["from", "to", "cc"],
                "addresses": ["chris.mallory@enron.com"],
                "case_insensitive": True,
            },
        )
        submission = _submission(
            answer=["chris.mallory@enron.com"],
            evidence_message_ids=[qualifying_id],
        )
        points, detail = grade_submission(
            submission,
            golden,
            5,
            mail_index=mail_index,
            challenge_prompt="Medium pack 'williams-w3__rt_strat'.",
            challenge_difficulty="medium",
        )
        assert detail.evidence_pass is True
        assert points == 5

    def test_predicate_extra_non_matching_evidence_ignored(self, mail_index) -> None:
        qualifying_id = "<30869027.1075846339788.JavaMail.evans@thyme>"
        non_matching_id = "<28841806.1075841866914.JavaMail.evans@thyme>"
        golden = _golden(
            value=24,
            evidence_message_ids=[qualifying_id],
            evidence_mode="predicate",
            evidence_predicate={
                "type": "from_address",
                "pack": "kean-s__enrononline",
                "from_address": "leonardo.pacheco@enron.com",
                "case_insensitive": True,
            },
        )
        submission = _submission(
            answer=24,
            evidence_message_ids=[non_matching_id, qualifying_id],
        )
        points, detail = grade_submission(
            submission,
            golden,
            5,
            mail_index=mail_index,
            challenge_prompt="Within the Medium pack 'kean-s__enrononline'.",
            challenge_difficulty="medium",
        )
        assert detail.evidence_pass is True
        assert points == 5

    def test_predicate_non_qualifying_only_fails(self, mail_index) -> None:
        non_matching_id = "<28841806.1075841866914.JavaMail.evans@thyme>"
        golden = _golden(
            value=24,
            evidence_message_ids=["<30869027.1075846339788.JavaMail.evans@thyme>"],
            evidence_mode="predicate",
            evidence_predicate={
                "type": "from_address",
                "pack": "kean-s__enrononline",
                "from_address": "leonardo.pacheco@enron.com",
                "case_insensitive": True,
            },
        )
        submission = _submission(answer=24, evidence_message_ids=[non_matching_id])
        points, detail = grade_submission(
            submission,
            golden,
            5,
            mail_index=mail_index,
            challenge_prompt="Within the Medium pack 'kean-s__enrononline'.",
            challenge_difficulty="medium",
        )
        assert detail.evidence_pass is False
        assert points == 0

    def test_predicate_correct_answer_missing_evidence_scores_zero(self, mail_index) -> None:
        golden = _golden(
            value=24,
            evidence_message_ids=["<30869027.1075846339788.JavaMail.evans@thyme>"],
            evidence_mode="predicate",
            evidence_predicate={
                "type": "from_address",
                "pack": "kean-s__enrononline",
                "from_address": "leonardo.pacheco@enron.com",
                "case_insensitive": True,
            },
        )
        submission = _submission(answer=24, evidence_message_ids=[])
        points, detail = grade_submission(
            submission,
            golden,
            5,
            mail_index=mail_index,
            challenge_prompt="Within the Medium pack 'kean-s__enrononline'.",
            challenge_difficulty="medium",
        )
        assert detail.evidence_pass is False
        assert points == 0


class TestSubmissionShape:
    def test_extra_submission_fields_ignored_for_scoring(self) -> None:
        golden = _golden(value="ok", evidence_message_ids=["<a@b>"])
        submission = _submission(
            answer="ok",
            evidence_message_ids=["<a@b>"],
            debug_trace=["step-1"],
            model="test-model",
        )
        points, detail = grade_submission(submission, golden, 2)
        assert points == 2
        assert detail.answer_match is True
        assert submission.model_dump(mode="json")["debug_trace"] == ["step-1"]

    def test_message_id_without_brackets_accepted(self) -> None:
        golden = _golden(value="ok", evidence_message_ids=["<a@b>"], evidence_mode="all")
        submission = _submission(answer="ok", evidence_message_ids=["a@b"])
        points, detail = grade_submission(submission, golden, 2)
        assert points == 2
        assert detail.evidence_pass is True
