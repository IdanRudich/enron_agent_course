"""Reference solution agent implementing the shared EnronAgent protocol."""

from __future__ import annotations

import sys

from enron_challenge.models import IndexResult, PublicChallengeRecord, StudentAgentSubmission

from enron_reference.indexer import build_index
from enron_reference.prompt_runtime import run_prompt


class ReferenceAgent:
    """Deterministic SQLite/FTS5 reference agent with PydanticAI prompt mode."""

    @property
    def name(self) -> str:
        return "enron-reference-agent"

    def index(self, dataset_path: str, index_dir: str) -> IndexResult:
        print(f"indexing {dataset_path} -> {index_dir}", file=sys.stderr)
        stats = build_index(dataset_path, index_dir)
        return IndexResult(
            status="ok",
            stats={
                "message_count": stats["message_count"],
                "duplicate_message_ids": stats["duplicate_message_ids"],
                "db_path": stats["db_path"],
            },
        )

    def prompt(
        self,
        dataset_path: str,
        index_dir: str,
        challenge: PublicChallengeRecord,
    ) -> StudentAgentSubmission:
        _ = dataset_path
        print(f"prompt {challenge.id}", file=sys.stderr)
        return run_prompt(index_dir, challenge)
