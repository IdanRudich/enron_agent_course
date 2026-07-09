"""Deterministic SQLite/FTS5 indexing over packaged Enron emails."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from email import policy
from email.parser import Parser
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterator

INDEX_DB_NAME = "messages.sqlite"
SCHEMA_VERSION = "1"

REPLY_PREFIXES = ("re:",)
FORWARD_PREFIXES = ("fw:", "fwd:")


@dataclass(frozen=True)
class ParsedEmail:
    message_id: str
    packaged_path: str
    pack: str | None
    mailbox: str | None
    folder: str | None
    source_type: str
    difficulty: str
    source_path: str | None
    source_provenance: str | None
    date_raw: str
    date_iso: str | None
    date_epoch: float | None
    from_raw: str
    to_raw: str
    cc_raw: str
    bcc_raw: str
    subject_raw: str
    subject_normalized: str
    is_reply: bool
    is_forward: bool
    is_reply_or_forward: bool
    body_text: str
    participants: tuple[tuple[str, str], ...]


def build_index(dataset_path: str | Path, index_dir: str | Path) -> dict[str, Any]:
    """Walk packaged mail, parse emails, and write a deterministic SQLite index."""
    dataset_root = Path(dataset_path).resolve()
    output_dir = Path(index_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / INDEX_DB_NAME

    if db_path.exists():
        db_path.unlink()

    pack_difficulty = _load_pack_difficulty(dataset_root)
    provenance = _load_source_provenance(dataset_root)
    parsed_rows = list(_iter_parsed_emails(dataset_root, pack_difficulty, provenance))

    connection = sqlite3.connect(db_path)
    try:
        _create_schema(connection)
        _insert_rows(connection, parsed_rows)
        _write_index_meta(connection, dataset_root, parsed_rows)
        connection.commit()
    finally:
        connection.close()

    return {
        "message_count": len(parsed_rows),
        "duplicate_message_ids": _count_duplicate_message_ids(parsed_rows),
        "db_path": str(db_path),
    }


def open_index(index_dir: str | Path) -> sqlite3.Connection:
    """Open the reference index database in the given directory."""
    db_path = Path(index_dir) / INDEX_DB_NAME
    if not db_path.is_file():
        raise FileNotFoundError(f"Index database not found: {db_path}")
    connection = sqlite3.connect(db_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE messages (
            row_id INTEGER PRIMARY KEY,
            message_id TEXT NOT NULL,
            packaged_path TEXT NOT NULL UNIQUE,
            pack TEXT,
            mailbox TEXT,
            folder TEXT,
            source_type TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            source_path TEXT,
            source_provenance TEXT,
            date_raw TEXT NOT NULL,
            date_iso TEXT,
            date_epoch REAL,
            from_raw TEXT NOT NULL,
            to_raw TEXT NOT NULL,
            cc_raw TEXT NOT NULL,
            bcc_raw TEXT NOT NULL,
            subject_raw TEXT NOT NULL,
            subject_normalized TEXT NOT NULL,
            is_reply INTEGER NOT NULL,
            is_forward INTEGER NOT NULL,
            is_reply_or_forward INTEGER NOT NULL,
            body_text TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE messages_fts USING fts5(
            body_text,
            content='messages',
            content_rowid='row_id'
        );

        CREATE TABLE participants (
            row_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            address TEXT NOT NULL,
            FOREIGN KEY (row_id) REFERENCES messages(row_id)
        );

        CREATE TABLE index_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE INDEX idx_messages_message_id ON messages(message_id);
        CREATE INDEX idx_messages_pack ON messages(pack);
        CREATE INDEX idx_messages_mailbox_folder ON messages(mailbox, folder);
        CREATE INDEX idx_participants_row_role ON participants(row_id, role);
        CREATE INDEX idx_participants_address ON participants(address);

        CREATE TRIGGER messages_ai AFTER INSERT ON messages BEGIN
            INSERT INTO messages_fts(rowid, body_text) VALUES (new.row_id, new.body_text);
        END;

        CREATE TRIGGER messages_ad AFTER DELETE ON messages BEGIN
            INSERT INTO messages_fts(messages_fts, rowid, body_text)
            VALUES ('delete', old.row_id, old.body_text);
        END;

        CREATE TRIGGER messages_au AFTER UPDATE ON messages BEGIN
            INSERT INTO messages_fts(messages_fts, rowid, body_text)
            VALUES ('delete', old.row_id, old.body_text);
            INSERT INTO messages_fts(rowid, body_text) VALUES (new.row_id, new.body_text);
        END;
        """
    )


def _insert_rows(connection: sqlite3.Connection, parsed_rows: list[ParsedEmail]) -> None:
    for row_id, row in enumerate(parsed_rows, start=1):
        connection.execute(
            """
            INSERT INTO messages (
                row_id, message_id, packaged_path, pack, mailbox, folder,
                source_type, difficulty, source_path, source_provenance,
                date_raw, date_iso, date_epoch,
                from_raw, to_raw, cc_raw, bcc_raw, subject_raw,
                subject_normalized, is_reply, is_forward, is_reply_or_forward,
                body_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                row.message_id,
                row.packaged_path,
                row.pack,
                row.mailbox,
                row.folder,
                row.source_type,
                row.difficulty,
                row.source_path,
                row.source_provenance,
                row.date_raw,
                row.date_iso,
                row.date_epoch,
                row.from_raw,
                row.to_raw,
                row.cc_raw,
                row.bcc_raw,
                row.subject_raw,
                row.subject_normalized,
                int(row.is_reply),
                int(row.is_forward),
                int(row.is_reply_or_forward),
                row.body_text,
            ),
        )
        connection.executemany(
            "INSERT INTO participants (row_id, role, address) VALUES (?, ?, ?)",
            [(row_id, role, address) for role, address in row.participants],
        )


def _write_index_meta(
    connection: sqlite3.Connection,
    dataset_root: Path,
    parsed_rows: list[ParsedEmail],
) -> None:
    meta = {
        "schema_version": SCHEMA_VERSION,
        "dataset_path": str(dataset_root),
        "message_count": len(parsed_rows),
        "packaged_paths": [row.packaged_path for row in parsed_rows],
    }
    connection.execute(
        "INSERT INTO index_meta (key, value) VALUES (?, ?)",
        ("build", json.dumps(meta, sort_keys=True)),
    )


def _iter_parsed_emails(
    dataset_root: Path,
    pack_difficulty: dict[str, str],
    provenance: dict[str, dict[str, Any]],
) -> Iterator[ParsedEmail]:
    repo_root = dataset_root.parent
    mail_root = dataset_root / "mail"

    full_root = mail_root / "full_mailboxes"
    if full_root.is_dir():
        for path in _iter_mail_files(full_root):
            rel = path.relative_to(full_root)
            parts = rel.parts
            if len(parts) < 3:
                continue
            mailbox = parts[0]
            folder = "/".join(parts[1:-1])
            source = provenance["mailboxes"].get(mailbox, {})
            file_source_path, file_source_provenance = _resolve_file_provenance(source, path.name)
            yield _parse_email_file(
                path=path,
                packaged_path=path.relative_to(repo_root).as_posix(),
                pack=None,
                mailbox=mailbox,
                folder=folder,
                source_type="full_mailbox",
                difficulty="easy",
                source_path=file_source_path,
                source_provenance=file_source_provenance,
            )

    packs_root = mail_root / "packs"
    if packs_root.is_dir():
        for path in _iter_mail_files(packs_root):
            rel = path.relative_to(packs_root)
            parts = rel.parts
            if len(parts) < 2:
                continue
            pack = parts[0]
            difficulty = pack_difficulty.get(pack)
            if difficulty not in {"medium", "hard"}:
                continue
            source = provenance["packs"].get(pack, {})
            file_source_path, file_source_provenance = _resolve_file_provenance(source, path.name)
            yield _parse_email_file(
                path=path,
                packaged_path=path.relative_to(repo_root).as_posix(),
                pack=pack,
                mailbox=None,
                folder=None,
                source_type="pack",
                difficulty=difficulty,
                source_path=file_source_path,
                source_provenance=file_source_provenance,
            )


def _iter_mail_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.name.startswith("."):
            yield path


def _parse_email_file(
    *,
    path: Path,
    packaged_path: str,
    pack: str | None,
    mailbox: str | None,
    folder: str | None,
    source_type: str,
    difficulty: str,
    source_path: str | None,
    source_provenance: str | None,
) -> ParsedEmail:
    text = path.read_text(encoding="utf-8", errors="replace")
    message = Parser(policy=policy.default).parsestr(text)

    message_id = _normalize_header_value(message.get("Message-ID"))
    if not message_id:
        raise ValueError(f"{packaged_path}: missing Message-ID header")

    subject_raw = _normalize_header_value(message.get("Subject"))
    subject_normalized, is_reply, is_forward, is_reply_or_forward = _classify_subject(subject_raw)
    date_raw = _extract_raw_date_header(text) or _normalize_header_value(message.get("Date"))
    date_iso, date_epoch = _parse_date(date_raw)
    body_text = _extract_body_text(message)

    participants: list[tuple[str, str]] = []
    for role, header_name in (
        ("from", "From"),
        ("to", "To"),
        ("cc", "Cc"),
        ("bcc", "Bcc"),
    ):
        participants.extend(
            (role, address)
            for address in _normalize_addresses(message.get(header_name))
        )

    return ParsedEmail(
        message_id=message_id,
        packaged_path=packaged_path,
        pack=pack,
        mailbox=mailbox,
        folder=folder,
        source_type=source_type,
        difficulty=difficulty,
        source_path=source_path,
        source_provenance=source_provenance,
        date_raw=date_raw,
        date_iso=date_iso,
        date_epoch=date_epoch,
        from_raw=_normalize_header_value(message.get("From")),
        to_raw=_normalize_header_value(message.get("To")),
        cc_raw=_normalize_header_value(message.get("Cc")),
        bcc_raw=_normalize_header_value(message.get("Bcc")),
        subject_raw=subject_raw,
        subject_normalized=subject_normalized,
        is_reply=is_reply,
        is_forward=is_forward,
        is_reply_or_forward=is_reply_or_forward,
        body_text=body_text,
        participants=tuple(participants),
    )


def _normalize_header_value(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_addresses(value: object) -> list[str]:
    return [
        address.strip().lower()
        for _, address in getaddresses([str(value or "")])
        if address.strip()
    ]


def _classify_subject(subject_raw: str) -> tuple[str, bool, bool, bool]:
    working = _normalize_header_value(subject_raw)
    is_reply = False
    is_forward = False

    changed = True
    while changed:
        changed = False
        lower = working.lower()
        for prefix in REPLY_PREFIXES:
            if lower.startswith(prefix):
                is_reply = True
                working = working[len(prefix) :].lstrip()
                changed = True
                break
        if changed:
            continue
        for prefix in FORWARD_PREFIXES:
            if lower.startswith(prefix):
                is_forward = True
                working = working[len(prefix) :].lstrip()
                changed = True
                break

    return working, is_reply, is_forward, is_reply or is_forward


def _extract_raw_date_header(text: str) -> str:
    for line in text.splitlines():
        if line.lower().startswith("date:"):
            return _normalize_header_value(line.split(":", 1)[1])
    return ""


def _resolve_file_provenance(source: dict[str, Any], filename: str) -> tuple[str | None, str | None]:
    provenance_list = source.get("source_provenance")
    if isinstance(provenance_list, list) and provenance_list:
        suffix = filename.rsplit("__", 1)[-1]
        if suffix.endswith("."):
            suffix = suffix[:-1]
        for entry in provenance_list:
            if not isinstance(entry, dict):
                continue
            entry_path = entry.get("source_path")
            if isinstance(entry_path, str) and (
                entry_path.endswith(f"/{suffix}.") or entry_path.endswith(f"/{suffix}")
            ):
                return entry_path, json.dumps(entry, sort_keys=True)
        return source.get("source_path"), json.dumps(provenance_list, sort_keys=True)

    source_path = source.get("source_path")
    if source_path:
        return source_path, json.dumps(source.get("source_provenance") or source_path, sort_keys=True)
    return None, None


def _parse_date(date_raw: str) -> tuple[str | None, float | None]:
    if not date_raw:
        return None, None
    try:
        parsed = parsedate_to_datetime(date_raw)
    except (TypeError, ValueError, OverflowError):
        return None, None
    return parsed.isoformat(), parsed.timestamp()


def _extract_body_text(message: Any) -> str:
    if message.is_multipart():
        parts: list[str] = []
        for part in message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get_content_disposition() == "attachment":
                continue
            if part.get_content_type() != "text/plain":
                continue
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            charset = part.get_content_charset() or "utf-8"
            parts.append(payload.decode(charset, errors="replace"))
        return "\n".join(parts)

    payload = message.get_payload(decode=True)
    if isinstance(payload, bytes):
        charset = message.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")
    if payload is None:
        return ""
    return str(payload)


def _load_pack_difficulty(dataset_root: Path) -> dict[str, str]:
    pack_difficulty: dict[str, str] = {}
    for difficulty in ("medium", "hard"):
        sources_path = dataset_root / "manifest" / f"sources_{difficulty}.json"
        if not sources_path.is_file():
            continue
        sources = json.loads(sources_path.read_text(encoding="utf-8"))
        for source in sources.get("sources", []):
            pack_name = source.get("pack_name") or Path(source.get("packaged_path", "")).name
            if pack_name:
                pack_difficulty[pack_name] = difficulty
    return pack_difficulty


def _load_source_provenance(dataset_root: Path) -> dict[str, dict[str, Any]]:
    mailboxes: dict[str, dict[str, Any]] = {}
    packs: dict[str, dict[str, Any]] = {}

    for difficulty in ("easy", "medium", "hard"):
        sources_path = dataset_root / "manifest" / f"sources_{difficulty}.json"
        if not sources_path.is_file():
            continue
        sources = json.loads(sources_path.read_text(encoding="utf-8"))
        for source in sources.get("sources", []):
            source_type = source.get("type")
            if source_type == "full_mailbox":
                mailbox = source.get("mailbox")
                if mailbox:
                    mailboxes[mailbox] = source
            else:
                pack_name = source.get("pack_name") or Path(source.get("packaged_path", "")).name
                if pack_name:
                    packs[pack_name] = source

    return {"mailboxes": mailboxes, "packs": packs}


def _count_duplicate_message_ids(parsed_rows: list[ParsedEmail]) -> int:
    counts: dict[str, int] = {}
    for row in parsed_rows:
        counts[row.message_id] = counts.get(row.message_id, 0) + 1
    return sum(1 for count in counts.values() if count > 1)
