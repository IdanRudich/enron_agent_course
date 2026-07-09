"""Tests for the reference solution SQLite/FTS5 index."""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from enron_reference.indexer import INDEX_DB_NAME, build_index, open_index

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "student_dataset"
SUBSET_DATASET = PROJECT_ROOT / "tests" / "fixtures" / "reference_subset_dataset"
DUPLICATE_MESSAGE_ID = "<19286900.1075842251199.JavaMail.evans@thyme>"


@pytest.fixture(scope="session")
def subset_dataset(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Small real-mail subset for fast parsing tests."""
    if SUBSET_DATASET.exists():
        return SUBSET_DATASET

    subset_root = tmp_path_factory.mktemp("reference_subset_dataset")
    mail_root = subset_root / "mail"
    manifest_root = subset_root / "manifest"
    manifest_root.mkdir(parents=True)

    for manifest_name in ("manifest.json", "sources_easy.json", "sources_medium.json", "sources_hard.json"):
        src = DATASET_PATH / "manifest" / manifest_name
        if src.is_file():
            shutil.copy2(src, manifest_root / manifest_name)

    copied_paths = [
        DATASET_PATH / "mail" / "full_mailboxes" / "crandell-s" / "inbox" / "134.",
        DATASET_PATH / "mail" / "full_mailboxes" / "dickson-s" / "sent" / "39.",
        DATASET_PATH / "mail" / "packs" / "kean-s__ferc" / "300.",
        DATASET_PATH / "mail" / "packs" / "symes-k__confirms" / "11.",
        DATASET_PATH / "mail" / "packs" / "cage_gas_cross_mailbox" / "hyvl-d__gas_cage__1.",
        DATASET_PATH / "mail" / "packs" / "cage_gas_termination_thread" / "hyvl-d__gas_cage__1.",
    ]
    for src in copied_paths:
        rel = src.relative_to(DATASET_PATH / "mail")
        dest = mail_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    return subset_root


def _fetch_one(connection: sqlite3.Connection, query: str, *params: object) -> sqlite3.Row:
    row = connection.execute(query, params).fetchone()
    assert row is not None
    return row


class TestReferenceIndexBuild:
    def test_index_creation_is_deterministic(self, subset_dataset: Path, tmp_path: Path) -> None:
        first_dir = tmp_path / "index-a"
        second_dir = tmp_path / "index-b"

        build_index(subset_dataset, first_dir)
        build_index(subset_dataset, second_dir)

        first_db = first_dir / INDEX_DB_NAME
        second_db = second_dir / INDEX_DB_NAME
        assert first_db.read_bytes() == second_db.read_bytes()

    def test_full_dataset_index_count(self, tmp_path: Path) -> None:
        stats = build_index(DATASET_PATH, tmp_path / "full-index")
        assert stats["message_count"] == 2892
        assert stats["duplicate_message_ids"] == 17

    def test_subprocess_index_command(self, subset_dataset: Path, tmp_path: Path) -> None:
        index_dir = tmp_path / "cli-index"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "enron_reference.cli",
                "index",
                str(subset_dataset),
                str(index_dir),
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        assert result.returncode == 0, result.stderr
        assert "indexing" in result.stderr
        payload = json.loads(result.stdout)
        assert payload["status"] == "ok"
        assert payload["stats"]["message_count"] == 6
        assert (index_dir / INDEX_DB_NAME).is_file()


class TestReferenceIndexSchema:
    def test_records_preserve_provenance_fields(self, subset_dataset: Path, tmp_path: Path) -> None:
        build_index(subset_dataset, tmp_path / "index")
        with open_index(tmp_path / "index") as connection:
            mailbox_row = _fetch_one(
                connection,
                """
                SELECT message_id, packaged_path, pack, mailbox, folder, source_type, difficulty
                FROM messages
                WHERE mailbox = ?
                """,
                "crandell-s",
            )
            assert mailbox_row["message_id"] == "<27940994.1075840056140.JavaMail.evans@thyme>"
            assert mailbox_row["packaged_path"] == (
                f"{subset_dataset.name}/mail/full_mailboxes/crandell-s/inbox/134."
            )
            assert mailbox_row["pack"] is None
            assert mailbox_row["mailbox"] == "crandell-s"
            assert mailbox_row["folder"] == "inbox"
            assert mailbox_row["source_type"] == "full_mailbox"
            assert mailbox_row["difficulty"] == "easy"

            pack_row = _fetch_one(
                connection,
                "SELECT pack, mailbox, folder, source_type, difficulty FROM messages WHERE pack = ?",
                "kean-s__ferc",
            )
            assert pack_row["mailbox"] is None
            assert pack_row["folder"] is None
            assert pack_row["source_type"] == "pack"
            assert pack_row["difficulty"] == "medium"

    def test_headers_are_separated_from_body(self, subset_dataset: Path, tmp_path: Path) -> None:
        build_index(subset_dataset, tmp_path / "index")
        with open_index(tmp_path / "index") as connection:
            row = _fetch_one(
                connection,
                """
                SELECT from_raw, subject_raw, body_text
                FROM messages
                WHERE mailbox = ?
                """,
                "crandell-s",
            )
            assert row["from_raw"] == "michael.tully@enron.com"
            assert row["subject_raw"] == "Forward obligations"
            assert "Message-ID:" not in row["body_text"]
            assert "Could one of you two send me the criteria" in row["body_text"]

    def test_date_parsing_preserves_offset(self, subset_dataset: Path, tmp_path: Path) -> None:
        build_index(subset_dataset, tmp_path / "index")
        with open_index(tmp_path / "index") as connection:
            row = _fetch_one(
                connection,
                "SELECT date_raw, date_iso, date_epoch FROM messages WHERE mailbox = ?",
                "crandell-s",
            )
            assert row["date_raw"] == "Tue, 23 Oct 2001 12:41:17 -0700 (PDT)"
            assert row["date_iso"] == "2001-10-23T12:41:17-07:00"
            assert isinstance(row["date_epoch"], float)

    def test_participant_roles_are_parsed(self, subset_dataset: Path, tmp_path: Path) -> None:
        build_index(subset_dataset, tmp_path / "index")
        with open_index(tmp_path / "index") as connection:
            row_id = _fetch_one(
                connection,
                "SELECT row_id FROM messages WHERE mailbox = ?",
                "crandell-s",
            )["row_id"]
            participants = connection.execute(
                "SELECT role, address FROM participants WHERE row_id = ? ORDER BY role, address",
                (row_id,),
            ).fetchall()
            assert [(row["role"], row["address"]) for row in participants] == [
                ("bcc", "diana.scholtes@enron.com"),
                ("cc", "diana.scholtes@enron.com"),
                ("from", "michael.tully@enron.com"),
                ("to", "sean.crandall@enron.com"),
            ]

    def test_subject_normalization_and_reply_forward_classification(
        self, subset_dataset: Path, tmp_path: Path
    ) -> None:
        build_index(subset_dataset, tmp_path / "index")
        with open_index(tmp_path / "index") as connection:
            reply_row = _fetch_one(
                connection,
                """
                SELECT subject_raw, subject_normalized, is_reply, is_forward, is_reply_or_forward
                FROM messages
                WHERE mailbox = ? AND folder = ?
                """,
                "dickson-s",
                "sent",
            )
            assert reply_row["subject_raw"] == "Re: B & J Gas & Oil"
            assert reply_row["subject_normalized"] == "B & J Gas & Oil"
            assert reply_row["is_reply"] == 1
            assert reply_row["is_forward"] == 0
            assert reply_row["is_reply_or_forward"] == 1

            forward_row = _fetch_one(
                connection,
                """
                SELECT subject_raw, subject_normalized, is_reply, is_forward, is_reply_or_forward
                FROM messages
                WHERE mailbox = ?
                """,
                "crandell-s",
            )
            assert forward_row["subject_raw"] == "Forward obligations"
            assert forward_row["subject_normalized"] == "Forward obligations"
            assert forward_row["is_reply"] == 0
            assert forward_row["is_forward"] == 0
            assert forward_row["is_reply_or_forward"] == 0

    def test_duplicate_message_ids_remain_distinct_rows(
        self, subset_dataset: Path, tmp_path: Path
    ) -> None:
        build_index(subset_dataset, tmp_path / "index")
        with open_index(tmp_path / "index") as connection:
            rows = connection.execute(
                """
                SELECT message_id, packaged_path, pack
                FROM messages
                WHERE message_id = ?
                ORDER BY packaged_path
                """,
                (DUPLICATE_MESSAGE_ID,),
            ).fetchall()
            assert len(rows) == 2
            assert {row["pack"] for row in rows} == {
                "cage_gas_cross_mailbox",
                "cage_gas_termination_thread",
            }
            assert rows[0]["packaged_path"] != rows[1]["packaged_path"]

    def test_packaged_path_provenance_is_recorded(self, subset_dataset: Path, tmp_path: Path) -> None:
        build_index(subset_dataset, tmp_path / "index")
        with open_index(tmp_path / "index") as connection:
            row = _fetch_one(
                connection,
                """
                SELECT packaged_path, source_path, source_provenance
                FROM messages
                WHERE pack = ?
                """,
                "cage_gas_cross_mailbox",
            )
            assert row["packaged_path"].endswith(
                "mail/packs/cage_gas_cross_mailbox/hyvl-d__gas_cage__1."
            )
            assert row["source_path"] == "enron_mail_20150507/maildir/hyvl-d/gas/cage/1."
            provenance = json.loads(row["source_provenance"])
            assert provenance["mailbox"] == "hyvl-d"
            assert provenance["folder"] == "gas/cage"


class TestReferenceIndexSearch:
    def test_fts5_search_finds_body_terms(self, subset_dataset: Path, tmp_path: Path) -> None:
        build_index(subset_dataset, tmp_path / "index")
        with open_index(tmp_path / "index") as connection:
            hits = connection.execute(
                """
                SELECT m.message_id, m.packaged_path
                FROM messages_fts fts
                JOIN messages m ON m.row_id = fts.rowid
                WHERE messages_fts MATCH ?
                """,
                ("criteria Forward obs",),
            ).fetchall()
            assert len(hits) == 1
            assert hits[0]["message_id"] == "<27940994.1075840056140.JavaMail.evans@thyme>"

    def test_prompt_command_requires_agent_configuration(self, tmp_path: Path) -> None:
        index_dir = tmp_path / "index"
        build_index(DATASET_PATH, index_dir)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "enron_reference.cli",
                "prompt",
                str(DATASET_PATH),
                str(index_dir),
                "easy-001",
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            env={
                **dict(**__import__("os").environ),
                "ENRON_AGENT_API_KEY": "",
                "ENRON_AGENT_MINIMAX_API_KEY": "",
                "ENRON_AGENT_MODEL": "",
            },
        )
        assert result.returncode == 1
        assert result.stdout == ""
        assert "missing required environment variable" in result.stderr.lower()
