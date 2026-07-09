"""Reusable Agent CLI Adapter for EnronAgent implementations."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from pydantic import BaseModel, ValidationError

from enron_challenge.dataset import load_public_challenge
from enron_challenge.errors import InvalidJsonError, InvalidSubmissionError, ProtocolError
from enron_challenge.models import AgentMetadata, IndexResult, StudentAgentSubmission
from enron_challenge.protocol import EnronAgent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Enron Challenge student agent CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("metadata", help="Return agent metadata")

    index_parser = subparsers.add_parser("index", help="Build a searchable index")
    index_parser.add_argument("dataset_path", help="Path to the packaged dataset")
    index_parser.add_argument("index_dir", help="Directory to write the index")

    prompt_parser = subparsers.add_parser("prompt", help="Answer one challenge")
    prompt_parser.add_argument("dataset_path", help="Path to the packaged dataset")
    prompt_parser.add_argument("index_dir", help="Prepared index directory")
    prompt_parser.add_argument("challenge_id", help="Challenge id from the golden set")

    return parser


def run_cli(agent: EnronAgent) -> None:
    """Parse argv and dispatch metadata, index, or prompt for one agent."""
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "metadata":
            _emit_json(AgentMetadata(agent_name=agent.name))
        elif args.command == "index":
            result = agent.index(args.dataset_path, args.index_dir)
            _emit_index_result(result)
        elif args.command == "prompt":
            challenge = load_public_challenge(args.dataset_path, args.challenge_id)
            result = agent.prompt(args.dataset_path, args.index_dir, challenge)
            _emit_submission(result)
    except ProtocolError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(exc.exit_code) from exc
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


def _emit_json(model: BaseModel) -> None:
    print(model.model_dump_json())


def _emit_index_result(result: Any) -> None:
    index_result = _coerce_model(result, IndexResult, InvalidSubmissionError, "index result")
    _emit_json(index_result)


def _emit_submission(result: Any) -> None:
    if isinstance(result, str):
        try:
            payload = json.loads(result)
        except json.JSONDecodeError as exc:
            raise InvalidJsonError(f"Invalid JSON: {exc}") from exc
        submission = _validate_model(
            payload,
            StudentAgentSubmission,
            InvalidSubmissionError,
            label="submission",
        )
        _emit_json(submission)
        return

    submission = _coerce_model(
        result,
        StudentAgentSubmission,
        InvalidSubmissionError,
        "submission",
    )
    _emit_json(submission)


def _coerce_model(
    result: Any,
    model_type: type[BaseModel],
    error_type: type[ProtocolError],
    label: str,
) -> BaseModel:
    if isinstance(result, model_type):
        return result
    if isinstance(result, dict):
        return _validate_model(result, model_type, error_type, label=label)
    raise error_type(f"Invalid {label}: expected {model_type.__name__}")


def _validate_model(
    payload: Any,
    model_type: type[BaseModel],
    error_type: type[ProtocolError],
    *,
    label: str = "submission",
) -> BaseModel:
    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        raise error_type(f"Invalid {label}: {exc}") from exc
