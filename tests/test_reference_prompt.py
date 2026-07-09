"""Mocked LLM tests for reference prompt runtime and submission shape."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic_ai import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.messages import ModelMessage

from enron_challenge.dataset import load_public_challenge, load_public_challenges
from enron_challenge.models import StudentAgentSubmission
from enron_eval.grader import grade_submission
from enron_eval.models import GoldenAnswer

from enron_reference.agent import ReferenceAgent
from enron_reference.indexer import build_index
from enron_reference.prompt_runtime import create_prompt_agent, run_prompt
from enron_reference.tools import IndexTools

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "student_dataset"
GOLDEN_SET_PATH = DATASET_PATH / "golden_set" / "golden_set.json"


def _load_golden(challenge_id: str) -> dict[str, Any]:
    records = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))
    for record in records:
        if record["id"] == challenge_id:
            return record
    raise KeyError(challenge_id)


@pytest.fixture(scope="module")
def indexed_dataset(tmp_path_factory: pytest.TempPathFactory) -> Path:
    index_dir = tmp_path_factory.mktemp("prompt-index")
    build_index(DATASET_PATH, index_dir)
    return index_dir


def _final_submission(
    challenge_id: str,
    answer: Any,
    evidence: list[str],
    info: AgentInfo,
) -> ModelResponse:
    payload = StudentAgentSubmission(
        challenge_id=challenge_id,
        answer=answer,
        evidence_message_ids=evidence,
    )
    if info.output_tools:
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, payload.model_dump())])
    return ModelResponse(parts=[TextPart(payload.model_dump_json())])


def _tool_then_answer(
    tool_name: str,
    tool_args: dict[str, Any],
    challenge_id: str,
    answer: Any,
    evidence: list[str],
):
    def model_function(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        tool_returns = [
            part for message in messages for part in message.parts if part.part_kind == "tool-return"
        ]
        if not tool_returns:
            return ModelResponse(parts=[ToolCallPart(tool_name, tool_args)])
        return _final_submission(challenge_id, answer, evidence, info)

    return model_function


class TestPromptRuntime:
    def test_create_prompt_agent_exposes_all_tools(self, indexed_dataset: Path) -> None:
        tools = IndexTools(str(indexed_dataset))
        try:
            agent = create_prompt_agent(tools, model=TestModel())
            tool_names = {tool.name for tool in agent._function_toolset.tools.values()}  # noqa: SLF001
            assert tool_names == {
                "get_message",
                "search_messages",
                "count_messages",
                "aggregate_messages",
                "list_pack_messages",
                "list_folder_messages",
            }
        finally:
            tools.close()

    def test_mocked_easy_lookup_submission_shape(self, indexed_dataset: Path) -> None:
        challenge = load_public_challenge(DATASET_PATH, "easy-003")
        golden = _load_golden("easy-003")
        model = FunctionModel(
            _tool_then_answer(
                "get_message",
                {"message_id": golden["golden_answer"]["evidence_message_ids"][0]},
                "easy-003",
                golden["golden_answer"]["accepted_answer"]["value"],
                golden["golden_answer"]["evidence_message_ids"],
            )
        )
        submission = run_prompt(str(indexed_dataset), challenge, model=model)
        assert submission.challenge_id == "easy-003"
        assert submission.answer == "david.steiner@enron.com"
        assert submission.evidence_message_ids == golden["golden_answer"]["evidence_message_ids"]

    def test_mocked_search_discovery_submission(self, indexed_dataset: Path) -> None:
        challenge = load_public_challenge(DATASET_PATH, "easy-002")
        golden = _load_golden("easy-002")
        model = FunctionModel(
            _tool_then_answer(
                "search_messages",
                {
                    "filters": {
                        "mailbox": "phanis-s",
                        "folder": "inbox",
                        "from_address": "sara.shackleton@enron.com",
                        "subject_exact": "Magnum Hunter Resources, Inc.",
                    },
                    "limit": 5,
                },
                "easy-002",
                golden["golden_answer"]["accepted_answer"]["value"],
                golden["golden_answer"]["evidence_message_ids"],
            )
        )
        submission = run_prompt(str(indexed_dataset), challenge, model=model)
        assert submission.answer == "<8294594.1075855414353.JavaMail.evans@thyme>"

    def test_reference_agent_prompt_cli_shape(self, indexed_dataset: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        challenge = load_public_challenge(DATASET_PATH, "easy-004")
        golden = _load_golden("easy-004")

        def fake_run_prompt(index_dir: str, loaded: Any, *, model: Any = None) -> StudentAgentSubmission:
            _ = index_dir, model
            return StudentAgentSubmission(
                challenge_id=loaded.id,
                answer=golden["golden_answer"]["accepted_answer"]["value"],
                evidence_message_ids=golden["golden_answer"]["evidence_message_ids"],
            )

        monkeypatch.setattr("enron_reference.agent.run_prompt", fake_run_prompt)
        submission = ReferenceAgent().prompt(str(DATASET_PATH), str(indexed_dataset), challenge)
        assert submission.challenge_id == "easy-004"
        assert submission.evidence_message_ids


class TestReferenceEvalRecording:
    @pytest.mark.parametrize(
        "challenge_id",
        [
            "easy-001",
            "easy-003",
            "medium-001",
            "medium-003",
            "hard-001",
        ],
    )
    def test_mocked_golden_answers_grade_full_points(
        self,
        indexed_dataset: Path,
        challenge_id: str,
    ) -> None:
        _ = indexed_dataset
        challenge = load_public_challenge(DATASET_PATH, challenge_id)
        golden_record = _load_golden(challenge_id)
        golden = GoldenAnswer.model_validate(golden_record["golden_answer"])
        submission = StudentAgentSubmission(
            challenge_id=challenge_id,
            answer=golden.accepted_answer.value,
            evidence_message_ids=golden.evidence_message_ids,
        )
        points, detail = grade_submission(
            submission,
            golden,
            challenge.points,
            dataset_path=DATASET_PATH,
            challenge_prompt=challenge.prompt,
            challenge_difficulty=challenge.difficulty,
        )
        assert detail.answer_match is True
        assert detail.evidence_pass is True
        assert points == challenge.points

    def test_difficulty_subsets_exist(self) -> None:
        challenges = load_public_challenges(DATASET_PATH)
        by_difficulty = {"easy": 0, "medium": 0, "hard": 0}
        for challenge in challenges:
            by_difficulty[challenge.difficulty] += 1
        assert by_difficulty == {"easy": 10, "medium": 10, "hard": 8}
