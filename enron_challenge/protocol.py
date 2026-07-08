"""EnronAgent protocol definition."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from enron_challenge.models import IndexResult, PublicChallengeRecord, StudentAgentSubmission


@runtime_checkable
class EnronAgent(Protocol):
    """Protocol-style interface implemented by agent packages."""

    @property
    def name(self) -> str:
        """Human-readable agent identity."""

    def index(self, dataset_path: str, index_dir: str) -> IndexResult:
        """Build a searchable index over the packaged dataset."""

    def prompt(
        self,
        dataset_path: str,
        index_dir: str,
        challenge: PublicChallengeRecord,
    ) -> StudentAgentSubmission:
        """Answer one challenge using the prepared index."""
