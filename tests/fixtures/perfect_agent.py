"""Perfect fake agent that returns golden answers for every challenge."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from enron_challenge.cli import run_cli
from enron_challenge.models import IndexResult, StudentAgentSubmission


class PerfectAgent:
    @property
    def name(self) -> str:
        return "perfect-fake-agent"

    def index(self, dataset_path: str, index_dir: str) -> IndexResult:
        print(f"indexing {dataset_path} -> {index_dir}", file=sys.stderr)
        return IndexResult(status="ok", stats={"indexed": True})

    def prompt(
        self,
        dataset_path: str,
        index_dir: str,
        challenge,
    ) -> StudentAgentSubmission:
        print(f"solving {challenge.id}", file=sys.stderr)
        golden = _load_golden_answer(dataset_path, challenge.id)
        accepted = golden["accepted_answer"]
        return StudentAgentSubmission(
            challenge_id=challenge.id,
            answer=accepted["value"],
            evidence_message_ids=list(golden["evidence_message_ids"]),
        )


def _load_golden_answer(dataset_path: str, challenge_id: str) -> dict:
    dataset_root = Path(dataset_path)
    manifest_path = dataset_root / "manifest" / "manifest.json"
    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    golden_set_path = dataset_root / manifest["files"]["golden_set"]
    with golden_set_path.open(encoding="utf-8") as handle:
        records = json.load(handle)
    for record in records:
        if record["id"] == challenge_id:
            return record["golden_answer"]
    raise KeyError(f"Unknown challenge id: {challenge_id}")


def main() -> None:
    run_cli(PerfectAgent())


if __name__ == "__main__":
    main()
