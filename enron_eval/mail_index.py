"""Build a Message-ID lookup index from packaged raw mail for predicate evidence."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from email import policy
from email.parser import Parser
from email.utils import getaddresses
from functools import lru_cache
from pathlib import Path
from typing import Any

MSG_ID_RE = re.compile(r"^<[^>]+>$")
PROMPT_PACK_RE = re.compile(r"(?:pack\s+['`]([^'`]+)['`]|['`]([^'`]+)['`]\s+pack)", re.IGNORECASE)
PROMPT_MAILBOX_FOLDER_RE = re.compile(r"\b([a-z0-9-]+) mailbox \(([^)]+) folder\)", re.IGNORECASE)
ADDRESS_ROLES = ("from", "to", "cc")


class MailIndex:
    """Lookup table mapping Message-IDs to parsed header rows."""

    def __init__(self, rows_by_mid: dict[str, list[dict[str, Any]]]) -> None:
        self._rows_by_mid = rows_by_mid

    def rows_for_message_id(self, message_id: str) -> list[dict[str, Any]]:
        return list(self._rows_by_mid.get(message_id, []))


def normalize_message_id(message_id: str) -> str | None:
    """Trim whitespace and accept add-only angle-bracket tolerance."""
    trimmed = " ".join(message_id.strip().split())
    if MSG_ID_RE.match(trimmed):
        return trimmed
    if trimmed and "@" in trimmed and "<" not in trimmed and ">" not in trimmed:
        bracketed = f"<{trimmed}>"
        if MSG_ID_RE.match(bracketed):
            return bracketed
    return None


def prompt_pack_names(prompt: str) -> set[str]:
    return {a or b for a, b in PROMPT_PACK_RE.findall(prompt)}


def prompt_mailbox_folders(prompt: str) -> tuple[set[str], set[str]]:
    mailboxes: set[str] = set()
    folders: set[str] = set()
    for mailbox, folder in PROMPT_MAILBOX_FOLDER_RE.findall(prompt):
        mailboxes.add(mailbox)
        folders.add(folder)
    return mailboxes, folders


def rows_matching_prompt_bounds(
    mid: str,
    *,
    difficulty: str,
    prompt: str,
    mail_index: MailIndex,
) -> list[dict[str, Any]]:
    packs = prompt_pack_names(prompt)
    mailboxes, folders = prompt_mailbox_folders(prompt)
    rows = [r for r in mail_index.rows_for_message_id(mid) if r.get("difficulty") == difficulty]
    if packs:
        rows = [r for r in rows if r.get("pack") in packs]
    if difficulty == "easy" and mailboxes:
        rows = [r for r in rows if r.get("mailbox") in mailboxes]
    if difficulty == "easy" and folders:
        rows = [r for r in rows if r.get("folder") in folders]
    return rows


def comparable(value: str, case_insensitive: bool) -> str:
    return value.casefold() if case_insensitive else value


def predicate_matches_row(predicate: dict[str, Any], row: dict[str, Any]) -> bool:
    if row.get("pack") != predicate.get("pack"):
        return False

    ptype = predicate.get("type")
    if ptype == "message_in_pack":
        return True

    case_insensitive = predicate.get("case_insensitive") is True
    if ptype == "subject_prefix":
        subject = row.get("subject") or ""
        if predicate.get("trim_subject") is True:
            subject = subject.strip()
        subject = comparable(subject, case_insensitive)
        prefixes = [comparable(prefix, case_insensitive) for prefix in predicate.get("subject_prefixes", [])]
        return any(subject.startswith(prefix) for prefix in prefixes)

    if ptype == "from_address":
        target = comparable(predicate.get("from_address", ""), case_insensitive)
        return any(comparable(address, case_insensitive) == target for address in row.get("from_addresses", []))

    if ptype == "address_in_headers":
        targets = {comparable(address, case_insensitive) for address in predicate.get("addresses", [])}
        row_addresses: list[str] = []
        for role in predicate.get("roles", []):
            row_addresses.extend(row.get(f"{role}_addresses", []))
        return any(comparable(address, case_insensitive) in targets for address in row_addresses)

    return False


@lru_cache(maxsize=4)
def build_mail_index(dataset_path: str) -> MailIndex:
    root = Path(dataset_path)
    pack_difficulty = _build_pack_difficulty_map(root)
    rows_by_mid: dict[str, list[dict[str, Any]]] = defaultdict(list)

    full_root = root / "mail" / "full_mailboxes"
    for path in _iter_mail_files(full_root):
        rel = path.relative_to(full_root)
        parts = rel.parts
        if len(parts) < 3:
            continue
        headers = _parse_mail_headers(path)
        if not headers:
            continue
        mid = headers["message_id"]
        rows_by_mid[mid].append(
            {
                "message_id": mid,
                "difficulty": "easy",
                "pack": None,
                "packaged_path": str(path),
                "mailbox": parts[0],
                "folder": "/".join(parts[1:-1]),
                "subject": headers["subject"],
                "from_addresses": headers["from_addresses"],
                "to_addresses": headers["to_addresses"],
                "cc_addresses": headers["cc_addresses"],
            }
        )

    packs_root = root / "mail" / "packs"
    for path in _iter_mail_files(packs_root):
        rel = path.relative_to(packs_root)
        parts = rel.parts
        if len(parts) < 2:
            continue
        pack = parts[0]
        difficulty = pack_difficulty.get(pack)
        if difficulty not in ("medium", "hard"):
            continue
        headers = _parse_mail_headers(path)
        if not headers:
            continue
        mid = headers["message_id"]
        rows_by_mid[mid].append(
            {
                "message_id": mid,
                "difficulty": difficulty,
                "pack": pack,
                "packaged_path": str(path),
                "mailbox": None,
                "folder": None,
                "subject": headers["subject"],
                "from_addresses": headers["from_addresses"],
                "to_addresses": headers["to_addresses"],
                "cc_addresses": headers["cc_addresses"],
            }
        )

    return MailIndex(dict(rows_by_mid))


def _build_pack_difficulty_map(root: Path) -> dict[str, str]:
    pack_difficulty: dict[str, str] = {}
    for difficulty in ("medium", "hard"):
        sources_path = root / "manifest" / f"sources_{difficulty}.json"
        with sources_path.open(encoding="utf-8") as handle:
            sources = json.load(handle)
        for source in sources.get("sources", []):
            pack_name = source.get("pack_name") or Path(source.get("packaged_path", "")).name
            if pack_name:
                pack_difficulty[pack_name] = difficulty
    return pack_difficulty


def _iter_mail_files(mail_dir: Path):
    if not mail_dir.is_dir():
        return
    for path in sorted(mail_dir.rglob("*")):
        if path.is_file() and not path.name.startswith("."):
            yield path


def _normalize_header_value(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_addresses(value: object) -> list[str]:
    return [
        address.strip().lower()
        for _, address in getaddresses([str(value or "")])
        if address.strip()
    ]


def _parse_mail_headers(path: Path) -> dict[str, Any] | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        msg = Parser(policy=policy.default).parsestr(text, headersonly=True)
    except OSError:
        return None
    message_id = msg.get("Message-ID")
    if message_id is None:
        return None
    message_id = _normalize_header_value(message_id)
    if not MSG_ID_RE.match(message_id):
        return None
    return {
        "message_id": message_id,
        "subject": _normalize_header_value(msg.get("Subject")),
        "from_addresses": _normalize_addresses(msg.get("From")),
        "to_addresses": _normalize_addresses(msg.get("To")),
        "cc_addresses": _normalize_addresses(msg.get("Cc")),
    }
