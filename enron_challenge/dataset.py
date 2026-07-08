"""Load Public Challenge Records from the packaged dataset."""

from __future__ import annotations

import json
from pathlib import Path

from enron_challenge.models import ExpectedSubmission, PublicChallengeRecord


def load_manifest(dataset_path: str | Path) -> dict:
    manifest_path = Path(dataset_path) / "manifest" / "manifest.json"
    with manifest_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_public_challenges(dataset_path: str | Path) -> list[PublicChallengeRecord]:
    manifest = load_manifest(dataset_path)
    golden_set_path = Path(dataset_path) / manifest["files"]["golden_set"]
    with golden_set_path.open(encoding="utf-8") as handle:
        records = json.load(handle)
    return [_to_public(record) for record in records]


def load_public_challenge(dataset_path: str | Path, challenge_id: str) -> PublicChallengeRecord:
    for challenge in load_public_challenges(dataset_path):
        if challenge.id == challenge_id:
            return challenge
    raise KeyError(f"Unknown challenge id: {challenge_id}")


def _to_public(record: dict) -> PublicChallengeRecord:
    return PublicChallengeRecord(
        id=record["id"],
        difficulty=record["difficulty"],
        points=record["points"],
        prompt=record["prompt"],
        expected_submission=ExpectedSubmission(**record["expected_submission"]),
    )
