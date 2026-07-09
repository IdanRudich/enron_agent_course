"""Deterministic index tools over the reference SQLite/FTS5 store."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from typing import Any

from enron_reference.indexer import open_index

DEFAULT_LIMIT = 20
MAX_LIMIT = 500


@dataclass
class MessageFilters:
    message_id: str | None = None
    from_address: str | None = None
    to_address: str | None = None
    cc_address: str | None = None
    any_participant: str | None = None
    subject_exact: str | None = None
    subject_prefix_any: list[str] | None = None
    date_start: str | None = None
    date_end: str | None = None
    pack_name: str | None = None
    mailbox: str | None = None
    folder: str | None = None
    include_subfolders: bool = False

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None) -> MessageFilters:
        if not data:
            return cls()
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{key: data[key] for key in data if key in known})


@dataclass
class IndexTools:
    index_dir: str
    _connection: sqlite3.Connection | None = field(default=None, repr=False)

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = open_index(self.index_dir)
        return self._connection

    def get_message(
        self,
        *,
        message_id: str | None = None,
        row_id: int | None = None,
        packaged_path: str | None = None,
        scope: dict[str, Any] | None = None,
        include_body: bool = True,
    ) -> dict[str, Any]:
        """Look up one or more messages by Message-ID, row id, or packaged path."""
        message_id = _coerce_optional_str(message_id)
        packaged_path = _coerce_optional_str(packaged_path)
        lookup_count = sum(value is not None for value in (message_id, row_id, packaged_path))
        if lookup_count != 1:
            return {
                "status": "error",
                "error": "Provide exactly one of message_id, row_id, or packaged_path",
                "hint": (
                    "For prompts that name a Message-ID, call lookup_by_message_id with that id "
                    "(including angle brackets). Use row_id or packaged_path only when the prompt "
                    "names those identifiers."
                ),
            }

        filters = MessageFilters.from_mapping(scope)
        if message_id is not None:
            filters.message_id = message_id
        where_sql, params = _build_where_clause(filters, alias="m")
        if row_id is not None:
            where_sql = "m.row_id = ?"
            params = [row_id]
        elif packaged_path is not None:
            where_sql = "m.packaged_path = ?"
            params = [packaged_path]

        rows = self._fetch_rows(
            f"SELECT m.* FROM messages m WHERE {where_sql} ORDER BY m.packaged_path",
            params,
        )
        if not rows:
            return {"status": "not_found", "matches": []}

        matches = [_row_to_message(row, include_body=include_body, connection=self.connection) for row in rows]
        if len(matches) == 1:
            return {"status": "found", "message": matches[0], "matches": matches}
        return {"status": "ambiguous", "matches": matches}

    def lookup_by_message_id(
        self,
        message_id: str,
        *,
        scope: dict[str, Any] | None = None,
        include_body: bool = True,
    ) -> dict[str, Any]:
        """Fetch a message by Message-ID (the common case for direct email lookups)."""
        return self.get_message(
            message_id=message_id,
            scope=scope,
            include_body=include_body,
        )

    def search_messages(
        self,
        *,
        query: str | None = None,
        limit: int = DEFAULT_LIMIT,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        order: str = "asc",
    ) -> dict[str, Any]:
        """Search messages with optional FTS query and structured metadata filters."""
        limit = _clamp_limit(limit)
        parsed_filters = MessageFilters.from_mapping(filters)
        order_sql = _order_clause(order_by, order)

        if query:
            fts_query = _fts_query(query)
            where_sql, params = _build_where_clause(parsed_filters, alias="m")
            sql = f"""
                SELECT m.*
                FROM messages_fts fts
                JOIN messages m ON m.row_id = fts.rowid
                WHERE messages_fts MATCH ? AND {where_sql}
                {order_sql}
                LIMIT ?
            """
            rows = self._fetch_rows(sql, [fts_query, *params, limit])
        else:
            where_sql, params = _build_where_clause(parsed_filters, alias="m")
            rows = self._fetch_rows(
                f"SELECT m.* FROM messages m WHERE {where_sql} {order_sql} LIMIT ?",
                [*params, limit],
            )

        return {
            "count": len(rows),
            "messages": [_row_to_summary(row) for row in rows],
        }

    def count_messages(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return an exact count of packaged rows matching structured filters."""
        where_sql, params = _build_where_clause(MessageFilters.from_mapping(filters), alias="m")
        row = self.connection.execute(
            f"SELECT COUNT(*) AS count FROM messages m WHERE {where_sql}",
            params,
        ).fetchone()
        return {"count": int(row["count"])}

    def aggregate_messages(
        self,
        filters: dict[str, Any] | None = None,
        *,
        distinct: str | None = None,
        metric: str | None = None,
        group_by: str | None = None,
        limit: int = MAX_LIMIT,
    ) -> dict[str, Any]:
        """Run deterministic aggregations over filtered messages."""
        parsed_filters = MessageFilters.from_mapping(filters)
        where_sql, params = _build_where_clause(parsed_filters, alias="m")

        if distinct:
            return self._aggregate_distinct(where_sql, params, distinct, limit)
        if metric in {"min_date", "max_date"}:
            return self._aggregate_date_extrema(where_sql, params, metric)
        if group_by:
            return self._aggregate_group_by(where_sql, params, group_by, limit)
        if metric == "count" or metric is None:
            return self.count_messages(filters)
        raise ValueError(f"Unsupported aggregate operation: distinct={distinct!r}, metric={metric!r}, group_by={group_by!r}")

    def list_pack_messages(
        self,
        pack_name: str,
        *,
        order_by: str = "date",
        order: str = "asc",
        limit: int | None = None,
        offset: int = 0,
        include_body: bool = False,
    ) -> dict[str, Any]:
        """List messages in a curated pack with sortable metadata rows."""
        filters = {"pack_name": pack_name}
        order_sql = _order_clause(order_by, order)
        sql = f"""
            SELECT m.* FROM messages m
            WHERE m.pack = ?
            {order_sql}
        """
        params: list[Any] = [pack_name]
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([_clamp_limit(limit), max(offset, 0)])
        rows = self._fetch_rows(sql, params)
        return {
            "pack_name": pack_name,
            "count": len(rows),
            "messages": [
                _row_to_message(row, include_body=include_body, connection=self.connection)
                if include_body
                else _row_to_summary(row)
                for row in rows
            ],
        }

    def list_folder_messages(
        self,
        mailbox: str,
        folder: str,
        *,
        include_subfolders: bool = False,
        order_by: str = "date",
        order: str = "asc",
        limit: int | None = None,
        offset: int = 0,
        include_body: bool = False,
    ) -> dict[str, Any]:
        """List messages in a mailbox folder, exact or recursive."""
        filters = MessageFilters(
            mailbox=mailbox,
            folder=folder,
            include_subfolders=include_subfolders,
        )
        where_sql, params = _build_where_clause(filters, alias="m")
        order_sql = _order_clause(order_by, order)
        sql = f"SELECT m.* FROM messages m WHERE {where_sql} {order_sql}"
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([_clamp_limit(limit), max(offset, 0)])
        rows = self._fetch_rows(sql, params)
        return {
            "mailbox": mailbox,
            "folder": folder,
            "include_subfolders": include_subfolders,
            "count": len(rows),
            "messages": [
                _row_to_message(row, include_body=include_body, connection=self.connection)
                if include_body
                else _row_to_summary(row)
                for row in rows
            ],
        }

    def _fetch_rows(self, sql: str, params: list[Any]) -> list[sqlite3.Row]:
        return list(self.connection.execute(sql, params).fetchall())

    def _aggregate_distinct(
        self,
        where_sql: str,
        params: list[Any],
        distinct: str,
        limit: int,
    ) -> dict[str, Any]:
        role_map = {
            "from_address": ("from",),
            "to_address": ("to",),
            "cc_address": ("cc",),
            "participants_from_to_cc": ("from", "to", "cc"),
        }
        if distinct not in role_map:
            raise ValueError(f"Unsupported distinct field: {distinct}")
        roles = role_map[distinct]
        placeholders = ", ".join("?" for _ in roles)
        sql = f"""
            SELECT DISTINCT p.address
            FROM messages m
            JOIN participants p ON p.row_id = m.row_id
            WHERE {where_sql} AND p.role IN ({placeholders})
            ORDER BY p.address
            LIMIT ?
        """
        rows = self.connection.execute(sql, [*params, *roles, _clamp_limit(limit)]).fetchall()
        values = [row["address"] for row in rows]
        supporting = self.search_messages(
            filters=_filters_from_params(where_sql, params),
            limit=min(len(values), 50),
        )["messages"]
        return {
            "distinct": distinct,
            "values": values,
            "count": len(values),
            "supporting_messages": supporting,
        }

    def _aggregate_date_extrema(
        self,
        where_sql: str,
        params: list[Any],
        metric: str,
    ) -> dict[str, Any]:
        direction = "ASC" if metric == "min_date" else "DESC"
        sql = f"""
            SELECT m.*
            FROM messages m
            WHERE {where_sql} AND m.date_epoch IS NOT NULL
            ORDER BY m.date_epoch {direction}, m.packaged_path ASC
            LIMIT 1
        """
        row = self.connection.execute(sql, params).fetchone()
        if row is None:
            return {"metric": metric, "message": None, "supporting_messages": []}
        message = _row_to_summary(row)
        return {
            "metric": metric,
            "message": message,
            "supporting_messages": [message],
        }

    def _aggregate_group_by(
        self,
        where_sql: str,
        params: list[Any],
        group_by: str,
        limit: int,
    ) -> dict[str, Any]:
        if group_by not in {"subject_normalized", "subject_raw"}:
            raise ValueError(f"Unsupported group_by field: {group_by}")
        column = group_by
        sql = f"""
            SELECT m.{column} AS group_key, COUNT(*) AS count,
                   GROUP_CONCAT(m.message_id) AS message_ids
            FROM messages m
            WHERE {where_sql}
            GROUP BY m.{column}
            ORDER BY count DESC, group_key ASC
            LIMIT ?
        """
        rows = self.connection.execute(sql, [*params, _clamp_limit(limit)]).fetchall()
        groups = []
        for row in rows:
            message_ids = (row["message_ids"] or "").split(",")
            groups.append(
                {
                    "key": row["group_key"],
                    "count": row["count"],
                    "message_ids": message_ids,
                }
            )
        return {"group_by": group_by, "groups": groups, "count": len(groups)}


def _filters_from_params(where_sql: str, params: list[Any]) -> dict[str, Any]:
    """Best-effort reverse mapping for supporting-message lookups in tests."""
    _ = where_sql, params
    return {}


def _coerce_optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_message_id(message_id: str) -> str:
    trimmed = message_id.strip()
    if trimmed.startswith("<") and trimmed.endswith(">"):
        return trimmed
    return f"<{trimmed.strip('<>')}>"


def _normalize_address(address: str) -> str:
    return address.strip().lower()


def _clamp_limit(limit: int) -> int:
    return max(1, min(limit, MAX_LIMIT))


def _fts_query(query: str) -> str:
    tokens = re.findall(r"\w+", query)
    if not tokens:
        return query
    return " AND ".join(tokens)


def _order_clause(order_by: str | None, order: str) -> str:
    direction = "DESC" if order.lower() == "desc" else "ASC"
    if order_by in {None, "date"}:
        return f"ORDER BY m.date_epoch {direction}, m.packaged_path ASC"
    if order_by == "subject":
        return f"ORDER BY m.subject_raw {direction}, m.packaged_path ASC"
    if order_by == "path":
        return f"ORDER BY m.packaged_path {direction}"
    raise ValueError(f"Unsupported order_by: {order_by}")


def _build_where_clause(filters: MessageFilters, *, alias: str = "m") -> tuple[str, list[Any]]:
    clauses = ["1 = 1"]
    params: list[Any] = []

    if filters.message_id is not None:
        clauses.append(f"{alias}.message_id = ?")
        params.append(_normalize_message_id(filters.message_id))

    if filters.from_address is not None:
        clauses.append(_participant_exists(alias, "from", filters.from_address))
        params.append(_normalize_address(filters.from_address))

    if filters.to_address is not None:
        clauses.append(_participant_exists(alias, "to", filters.to_address))
        params.append(_normalize_address(filters.to_address))

    if filters.cc_address is not None:
        clauses.append(_participant_exists(alias, "cc", filters.cc_address))
        params.append(_normalize_address(filters.cc_address))

    if filters.any_participant is not None:
        clauses.append(
            f"EXISTS (SELECT 1 FROM participants p WHERE p.row_id = {alias}.row_id AND p.address = ?)"
        )
        params.append(_normalize_address(filters.any_participant))

    if filters.subject_exact is not None:
        clauses.append(f"LOWER(TRIM({alias}.subject_raw)) = LOWER(TRIM(?))")
        params.append(filters.subject_exact)

    if filters.subject_prefix_any:
        prefix_clauses = []
        for prefix in filters.subject_prefix_any:
            prefix_clauses.append(f"LOWER(TRIM({alias}.subject_raw)) LIKE ?")
            params.append(prefix.strip().lower() + "%")
        clauses.append("(" + " OR ".join(prefix_clauses) + ")")

    if filters.date_start is not None:
        clauses.append(f"{alias}.date_iso >= ?")
        params.append(filters.date_start)

    if filters.date_end is not None:
        clauses.append(f"{alias}.date_iso <= ?")
        params.append(filters.date_end)

    if filters.pack_name is not None:
        clauses.append(f"{alias}.pack = ?")
        params.append(filters.pack_name)

    if filters.mailbox is not None:
        clauses.append(f"{alias}.mailbox = ?")
        params.append(filters.mailbox)

    if filters.folder is not None:
        if filters.include_subfolders:
            clauses.append(f"({alias}.folder = ? OR {alias}.folder LIKE ?)")
            params.extend([filters.folder, f"{filters.folder}/%"])
        else:
            clauses.append(f"{alias}.folder = ?")
            params.append(filters.folder)

    return " AND ".join(clauses), params


def _participant_exists(alias: str, role: str, address: str) -> str:
    _ = address
    return (
        f"EXISTS (SELECT 1 FROM participants p "
        f"WHERE p.row_id = {alias}.row_id AND p.role = '{role}' AND p.address = ?)"
    )


def _addresses_for_row(connection: sqlite3.Connection, row_id: int) -> dict[str, list[str]]:
    participants = connection.execute(
        "SELECT role, address FROM participants WHERE row_id = ? ORDER BY role, address",
        (row_id,),
    ).fetchall()
    grouped: dict[str, list[str]] = {"from": [], "to": [], "cc": [], "bcc": []}
    for participant in participants:
        grouped.setdefault(participant["role"], []).append(participant["address"])
    return grouped


def _row_to_summary(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "row_id": row["row_id"],
        "message_id": row["message_id"],
        "packaged_path": row["packaged_path"],
        "pack": row["pack"],
        "mailbox": row["mailbox"],
        "folder": row["folder"],
        "date_raw": row["date_raw"],
        "date_iso": row["date_iso"],
        "date_epoch": row["date_epoch"],
        "from_raw": row["from_raw"],
        "to_raw": row["to_raw"],
        "cc_raw": row["cc_raw"],
        "subject_raw": row["subject_raw"],
        "subject_normalized": row["subject_normalized"],
        "is_reply": bool(row["is_reply"]),
        "is_forward": bool(row["is_forward"]),
        "is_reply_or_forward": bool(row["is_reply_or_forward"]),
    }


def _row_to_message(
    row: sqlite3.Row,
    *,
    include_body: bool,
    connection: sqlite3.Connection,
) -> dict[str, Any]:
    payload = _row_to_summary(row)
    payload.update(
        {
            "bcc_raw": row["bcc_raw"],
            "source_type": row["source_type"],
            "difficulty": row["difficulty"],
            "source_path": row["source_path"],
            "source_provenance": _maybe_json(row["source_provenance"]),
            "addresses_by_role": _addresses_for_row(connection, row["row_id"]),
        }
    )
    if include_body:
        payload["body_text"] = row["body_text"]
    return payload


def _maybe_json(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value
