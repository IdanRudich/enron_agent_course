"""Load Golden Set records with eval-only golden answer data."""

from __future__ import annotations

import json
from pathlib import Path

from enron_challenge.dataset import load_manifest
from enron_eval.models import GoldenChallengeRecord


def load_golden_challenges(dataset_path: str | Path) -> list[GoldenChallengeRecord]:
    manifest = load_manifest(dataset_path)
    golden_set_path = Path(dataset_path) / manifest["files"]["golden_set"]
    with golden_set_path.open(encoding="utf-8") as handle:
        records = json.load(handle)
    return [GoldenChallengeRecord.model_validate(record) for record in records]


def load_dataset_version(dataset_path: str | Path) -> str:
    manifest = load_manifest(dataset_path)
    return manifest["dataset_version"]
