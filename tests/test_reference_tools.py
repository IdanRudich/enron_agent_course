"""Deterministic tests for reference index tools (no LLM)."""

from __future__ import annotations

from pathlib import Path

import pytest

from enron_reference.indexer import build_index
from enron_reference.tools import IndexTools

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "student_dataset"
SUBSET_DATASET = PROJECT_ROOT / "tests" / "fixtures" / "reference_subset_dataset"
DUPLICATE_MESSAGE_ID = "<19286900.1075842251199.JavaMail.evans@thyme>"


@pytest.fixture(scope="module")
def subset_index(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, IndexTools]:
    dataset = SUBSET_DATASET if SUBSET_DATASET.exists() else DATASET_PATH
    index_dir = tmp_path_factory.mktemp("tools-subset-index")
    build_index(dataset, index_dir)
    tools = IndexTools(str(index_dir))
    yield index_dir, tools
    tools.close()


@pytest.fixture(scope="module")
def full_index(tmp_path_factory: pytest.TempPathFactory) -> IndexTools:
    index_dir = tmp_path_factory.mktemp("tools-full-index")
    build_index(DATASET_PATH, index_dir)
    tools = IndexTools(str(index_dir))
    yield tools
    tools.close()


class TestGetMessage:
    def test_lookup_by_message_id(self, subset_index: tuple[Path, IndexTools]) -> None:
        _, tools = subset_index
        result = tools.get_message(message_id="<27940994.1075840056140.JavaMail.evans@thyme>")
        assert result["status"] == "found"
        message = result["message"]
        assert message["from_raw"] == "michael.tully@enron.com"
        assert message["subject_raw"] == "Forward obligations"
        assert "Could one of you two send me the criteria" in message["body_text"]

    def test_lookup_by_packaged_path(self, subset_index: tuple[Path, IndexTools]) -> None:
        _, tools = subset_index
        by_id = tools.get_message(message_id="<27940994.1075840056140.JavaMail.evans@thyme>")
        packaged_path = by_id["message"]["packaged_path"]
        result = tools.get_message(packaged_path=packaged_path)
        assert result["status"] == "found"
        assert result["message"]["mailbox"] == "crandell-s"

    def test_ambiguous_message_id_returns_matches(self, subset_index: tuple[Path, IndexTools]) -> None:
        _, tools = subset_index
        result = tools.get_message(message_id=DUPLICATE_MESSAGE_ID, include_body=False)
        assert result["status"] == "ambiguous"
        assert len(result["matches"]) == 2
        assert {match["pack"] for match in result["matches"]} == {
            "cage_gas_cross_mailbox",
            "cage_gas_termination_thread",
        }
        assert all("body_text" not in match for match in result["matches"])

    def test_scope_disambiguates_duplicate_message_id(self, subset_index: tuple[Path, IndexTools]) -> None:
        _, tools = subset_index
        result = tools.get_message(
            message_id=DUPLICATE_MESSAGE_ID,
            scope={"pack_name": "cage_gas_cross_mailbox"},
        )
        assert result["status"] == "found"
        assert result["message"]["pack"] == "cage_gas_cross_mailbox"


class TestSearchMessages:
    def test_structured_sender_and_subject_filters(self, full_index: IndexTools) -> None:
        result = full_index.search_messages(
            filters={
                "mailbox": "phanis-s",
                "folder": "inbox",
                "from_address": "sara.shackleton@enron.com",
                "subject_exact": "Magnum Hunter Resources, Inc.",
            },
            limit=5,
        )
        assert result["count"] == 1
        assert result["messages"][0]["message_id"] == "<8294594.1075855414353.JavaMail.evans@thyme>"

    def test_fts_query_with_filters(self, subset_index: tuple[Path, IndexTools]) -> None:
        _, tools = subset_index
        result = tools.search_messages(
            query="criteria Forward obs",
            filters={"mailbox": "crandell-s"},
            limit=5,
        )
        assert result["count"] == 1
        assert result["messages"][0]["message_id"] == "<27940994.1075840056140.JavaMail.evans@thyme>"

    def test_date_ordering_asc_and_desc(self, full_index: IndexTools) -> None:
        earliest = full_index.search_messages(
            filters={"pack_name": "kean-s__ferc"},
            order_by="date",
            order="asc",
            limit=1,
        )
        latest = full_index.search_messages(
            filters={"pack_name": "kean-s__ferc"},
            order_by="date",
            order="desc",
            limit=1,
        )
        assert earliest["messages"][0]["date_iso"] == "2000-03-15T07:37:00-08:00"
        assert latest["messages"][0]["date_iso"] == "2001-12-06T08:31:59-08:00"


class TestCountMessages:
    def test_pack_count(self, full_index: IndexTools) -> None:
        result = full_index.count_messages({"pack_name": "symes-k__power_marketer"})
        assert result["count"] == 136

    def test_reply_forward_prefix_count(self, full_index: IndexTools) -> None:
        result = full_index.count_messages(
            {
                "pack_name": "steffes-j__credit_issues",
                "subject_prefix_any": ["re:", "fw:", "fwd:"],
            }
        )
        assert result["count"] == 51

    def test_exact_sender_in_pack(self, full_index: IndexTools) -> None:
        result = full_index.count_messages(
            {
                "pack_name": "kean-s__enrononline",
                "from_address": "leonardo.pacheco@enron.com",
            }
        )
        assert result["count"] == 24


class TestAggregateMessages:
    def test_min_date_returns_supporting_row(self, full_index: IndexTools) -> None:
        result = full_index.aggregate_messages(
            {"pack_name": "kean-s__ferc"},
            metric="min_date",
        )
        message = result["message"]
        assert message is not None
        assert message["message_id"] == "<26816706.1075846346223.JavaMail.evans@thyme>"
        assert message["date_iso"] == "2000-03-15T07:37:00-08:00"
        assert result["supporting_messages"]

    def test_max_date_returns_supporting_row(self, full_index: IndexTools) -> None:
        result = full_index.aggregate_messages(
            {"pack_name": "symes-k__scheduling"},
            metric="max_date",
        )
        message = result["message"]
        assert message is not None
        assert message["date_iso"] == "2001-05-01T07:45:00-07:00"

    def test_distinct_from_addresses(self, full_index: IndexTools) -> None:
        result = full_index.aggregate_messages(
            {"pack_name": "symes-k__scheduling"},
            distinct="from_address",
            limit=200,
        )
        assert "phillip.platter@enron.com" in result["values"]
        assert result["count"] >= 1

    def test_subject_grouping(self, full_index: IndexTools) -> None:
        result = full_index.aggregate_messages(
            {"pack_name": "symes-k__power_marketer"},
            group_by="subject_normalized",
            limit=5,
        )
        assert result["groups"]
        assert result["groups"][0]["count"] >= 1


class TestListTools:
    def test_list_pack_messages_metadata_only(self, full_index: IndexTools) -> None:
        result = full_index.list_pack_messages("kean-s__ferc", order_by="date", order="asc", limit=3)
        assert result["count"] == 3
        message = result["messages"][0]
        assert "body_text" not in message
        assert message["pack"] == "kean-s__ferc"

    def test_list_folder_exact_folder(self, full_index: IndexTools) -> None:
        result = full_index.list_folder_messages("phanis-s", "inbox", limit=10)
        assert result["count"] == 10
        assert all(message["folder"] == "inbox" for message in result["messages"])

    def test_list_folder_recursive_includes_subfolders(self, full_index: IndexTools) -> None:
        exact = full_index.list_folder_messages("crandell-s", "inbox", include_subfolders=False)
        recursive = full_index.list_folder_messages("crandell-s", "inbox", include_subfolders=True)
        assert recursive["count"] > exact["count"]
