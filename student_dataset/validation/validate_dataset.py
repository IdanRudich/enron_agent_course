#!/usr/bin/env python3
"""Golden Dataset consistency validator for the unified student corpus.

The student package intentionally does not ship a prebuilt evidence index. This
validator derives Message-ID evidence from the packaged raw mail files.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from email import policy
from email.parser import Parser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent
DIFFICULTIES = ("easy", "medium", "hard")
DIFFICULTY_ORDER = {difficulty: i for i, difficulty in enumerate(DIFFICULTIES)}

POINT_BANDS = {"easy": (1, 3), "medium": (4, 7), "hard": (8, 10)}
EXPECTED_CHALLENGE_COUNTS = {"easy": 10, "medium": 10, "hard": 8}

MSG_ID_RE = re.compile(r"^<[^>]+>$")
PROMPT_PACK_RE = re.compile(r"(?:pack\s+['`]([^'`]+)['`]|['`]([^'`]+)['`]\s+pack)", re.IGNORECASE)
PROMPT_MAILBOX_FOLDER_RE = re.compile(r"\b([a-z0-9-]+) mailbox \(([^)]+) folder\)", re.IGNORECASE)
SOURCE_CORPUS_PREFIX = "enron_mail_20150507/maildir/"
DATASET_MAIL_PREFIX = "student_dataset/mail/"
EXPECTED_FILES = {
    "golden_set": ROOT / "golden_set" / "golden_set.json",
}
OBSOLETE_FILES = [
    ROOT / "challenges" / "challenges.json",
    ROOT / "golden_answers" / "golden_answers.json",
] + [
    ROOT / "challenges" / f"challenges_{difficulty}.json"
    for difficulty in DIFFICULTIES
] + [
    ROOT / "golden_answers" / f"golden_{difficulty}.json"
    for difficulty in DIFFICULTIES
] + [
    ROOT / "evidence" / "evidence.jsonl",
] + [
    ROOT / "evidence" / f"evidence_{difficulty}.jsonl"
    for difficulty in DIFFICULTIES
]


@dataclass
class Report:
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)
    counts: dict = field(default_factory=dict)

    def fail(self, msg: str) -> None:
        self.failures.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def check(self, msg: str) -> None:
        self.checks.append(msg)


def load_json(path: Path) -> object:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def count_mail_files(mail_dir: Path) -> int:
    if not mail_dir.is_dir():
        return 0
    return sum(1 for p in mail_dir.rglob("*") if p.is_file() and not p.name.startswith("."))


def iter_mail_files(mail_dir: Path):
    if not mail_dir.is_dir():
        return
    for p in sorted(mail_dir.rglob("*")):
        if p.is_file() and not p.name.startswith("."):
            yield p


def dataset_relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def sum_source_email_counts(sources: dict) -> int:
    return sum(s.get("email_count", 0) for s in sources.get("sources", []))


def index_by_id(records: list[dict], label: str, report: Report) -> dict[str, dict]:
    out = {}
    for r in records:
        rid = r.get("id")
        if not isinstance(rid, str):
            report.fail(f"{label}: record missing string id: {r!r}")
            continue
        if rid in out:
            report.fail(f"{label}: duplicate id {rid}")
        out[rid] = r
    return out


def expected_sort(records: list[dict]) -> list[str]:
    return [
        r.get("id", "")
        for r in sorted(records, key=lambda r: (DIFFICULTY_ORDER.get(r.get("difficulty"), 99), r.get("id", "")))
    ]


def build_pack_difficulty_map(report: Report) -> dict[str, str]:
    pack_difficulty: dict[str, str] = {}
    for difficulty in ("medium", "hard"):
        sources = load_json(ROOT / "manifest" / f"sources_{difficulty}.json")
        for source in sources.get("sources", []):
            pack_name = source.get("pack_name") or Path(source.get("packaged_path", "")).name
            if not pack_name:
                report.fail(f"sources_{difficulty}: source missing pack name: {source!r}")
                continue
            previous = pack_difficulty.get(pack_name)
            if previous and previous != difficulty:
                report.fail(f"pack {pack_name!r}: appears as both {previous} and {difficulty}")
            pack_difficulty[pack_name] = difficulty
    return pack_difficulty


def validate_layout(report: Report) -> None:
    for label, path in EXPECTED_FILES.items():
        if not path.is_file():
            report.fail(f"missing unified {label} file: {path.relative_to(ROOT)}")
    for path in OBSOLETE_FILES:
        if path.exists():
            report.fail(f"obsolete split/evidence file remains: {path.relative_to(ROOT)}")
    evidence_dir = ROOT / "evidence"
    if evidence_dir.exists():
        report.fail("student package must not include an evidence/ directory")

    full_mailboxes = ROOT / "mail" / "full_mailboxes"
    packs = ROOT / "mail" / "packs"
    if not full_mailboxes.is_dir():
        report.fail("mail/full_mailboxes is missing")
    if not packs.is_dir():
        report.fail("mail/packs is missing")
    for old in ("easy", "medium", "hard"):
        if (ROOT / "mail" / old).exists():
            report.fail(f"obsolete mail/{old} directory remains")

    report.counts["mail_full_mailboxes_files"] = count_mail_files(full_mailboxes)
    report.counts["mail_packs_files"] = count_mail_files(packs)
    report.counts["mail_files_total"] = report.counts["mail_full_mailboxes_files"] + report.counts["mail_packs_files"]
    report.check(
        "mail layout: "
        f"{report.counts['mail_full_mailboxes_files']} full-mailbox files, "
        f"{report.counts['mail_packs_files']} pack files"
    )


def parse_message_id(path: Path, report: Report) -> str | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        msg = Parser(policy=policy.default).parsestr(text, headersonly=True)
    except Exception as exc:  # pragma: no cover - defensive for release scripts
        report.fail(f"{dataset_relative(path)}: failed to parse email headers: {exc}")
        return None
    message_id = msg.get("Message-ID")
    if message_id is None:
        report.fail(f"{dataset_relative(path)}: missing Message-ID header")
        return None
    message_id = " ".join(str(message_id).strip().split())
    if not MSG_ID_RE.match(message_id):
        report.fail(f"{dataset_relative(path)}: malformed Message-ID {message_id!r}")
        return None
    return message_id


def derive_mail_rows(pack_difficulty: dict[str, str], report: Report) -> dict[str, list[dict]]:
    rows_by_mid: dict[str, list[dict]] = defaultdict(list)
    difficulty_counts: Counter[str] = Counter()
    identity_counts: Counter[tuple[str, str, str | None]] = Counter()

    full_root = ROOT / "mail" / "full_mailboxes"
    for path in iter_mail_files(full_root):
        rel = path.relative_to(full_root)
        parts = rel.parts
        if len(parts) < 3:
            report.fail(f"{dataset_relative(path)}: full-mailbox file must be under <mailbox>/<folder>/<n>.")
            continue
        mid = parse_message_id(path, report)
        if not mid:
            continue
        row = {
            "message_id": mid,
            "difficulty": "easy",
            "pack": None,
            "packaged_path": dataset_relative(path),
            "mailbox": parts[0],
            "folder": "/".join(parts[1:-1]),
        }
        rows_by_mid[mid].append(row)
        difficulty_counts["easy"] += 1
        identity_counts[(mid, row["packaged_path"], None)] += 1

    packs_root = ROOT / "mail" / "packs"
    for path in iter_mail_files(packs_root):
        rel = path.relative_to(packs_root)
        parts = rel.parts
        if len(parts) < 2:
            report.fail(f"{dataset_relative(path)}: pack file must be under <pack_name>/<n>.")
            continue
        pack = parts[0]
        difficulty = pack_difficulty.get(pack)
        if difficulty not in ("medium", "hard"):
            report.fail(f"{dataset_relative(path)}: pack {pack!r} not found in medium/hard source fragments")
            continue
        mid = parse_message_id(path, report)
        if not mid:
            continue
        row = {
            "message_id": mid,
            "difficulty": difficulty,
            "pack": pack,
            "packaged_path": dataset_relative(path),
            "mailbox": None,
            "folder": None,
        }
        rows_by_mid[mid].append(row)
        difficulty_counts[difficulty] += 1
        identity_counts[(mid, row["packaged_path"], pack)] += 1

    for identity, count in identity_counts.items():
        if count > 1:
            report.fail(f"duplicate packaged mail identity {identity}: {count} rows")

    duplicate_mids = sum(1 for rows in rows_by_mid.values() if len(rows) > 1)
    total = sum(difficulty_counts.values())
    report.counts["parsed_mail_total"] = total
    for difficulty in DIFFICULTIES:
        report.counts[f"parsed_mail_{difficulty}"] = difficulty_counts[difficulty]
    report.counts["duplicate_message_ids_allowed"] = duplicate_mids
    report.check(f"parsed mail: {total} files with Message-ID headers, {duplicate_mids} duplicated Message-IDs")
    return rows_by_mid


def prompt_pack_names(prompt: str) -> set[str]:
    return {a or b for a, b in PROMPT_PACK_RE.findall(prompt)}


def prompt_mailbox_folders(prompt: str) -> tuple[set[str], set[str]]:
    mailboxes: set[str] = set()
    folders: set[str] = set()
    for mailbox, folder in PROMPT_MAILBOX_FOLDER_RE.findall(prompt):
        mailboxes.add(mailbox)
        folders.add(folder)
    return mailboxes, folders


def validate_prompt_bounds_explicit(challenge: dict, report: Report) -> None:
    cid = challenge.get("id", "<missing>")
    prompt = challenge.get("prompt", "")
    if not prompt or not prompt.strip():
        report.fail(f"{cid}: empty prompt")
        return
    if "family" in challenge:
        report.fail(f"{cid}: student-facing challenge record must not include family")
    if "scope" in challenge:
        report.fail(f"{cid}: student-facing challenge record must not include scope")
    prompt_packs = prompt_pack_names(prompt)
    prompt_mailboxes, prompt_folders = prompt_mailbox_folders(prompt)
    has_bound = bool(prompt_packs or (prompt_mailboxes and prompt_folders))
    search_words = ("search", "count", "how many", "list all", "list every", "earliest", "latest", "who")
    prompt_lower = prompt.lower()
    needs_explicit = any(w in prompt_lower for w in search_words)
    if needs_explicit and not has_bound:
        report.fail(f"{cid}: search-style prompt lacks prompt-visible scope bounds")


def validate_challenge(ch: dict, report: Report) -> None:
    cid = ch.get("id", "<missing>")
    difficulty = ch.get("difficulty")
    if difficulty not in DIFFICULTIES:
        report.fail(f"{cid}: invalid difficulty {difficulty!r}")
        return
    if not isinstance(cid, str) or not cid.startswith(f"{difficulty}-"):
        report.fail(f"{cid}: id prefix does not match difficulty {difficulty!r}")
    points = ch.get("points")
    lo, hi = POINT_BANDS[difficulty]
    if not isinstance(points, int) or not (lo <= points <= hi):
        report.fail(f"{cid}: points {points!r} outside {difficulty} band {lo}-{hi}")
    es = ch.get("expected_submission") or {}
    if es.get("requires_evidence_message_ids") is not True:
        report.fail(f"{cid}: expected_submission.requires_evidence_message_ids must be true")
    validate_prompt_bounds_explicit(ch, report)


def rows_matching_prompt_bounds(mid: str, challenge: dict, rows_by_mid: dict[str, list[dict]]) -> list[dict]:
    difficulty = challenge.get("difficulty")
    prompt = challenge.get("prompt", "")
    packs = prompt_pack_names(prompt)
    mailboxes, folders = prompt_mailbox_folders(prompt)
    rows = [r for r in rows_by_mid.get(mid, []) if r.get("difficulty") == difficulty]
    if packs:
        rows = [r for r in rows if r.get("pack") in packs]
    if difficulty == "easy" and mailboxes:
        rows = [r for r in rows if r.get("mailbox") in mailboxes]
    if difficulty == "easy" and folders:
        rows = [r for r in rows if r.get("folder") in folders]
    return rows


def validate_golden(ga: object, ch: dict, rows_by_mid: dict[str, list[dict]], report: Report) -> None:
    gid = ch.get("id", "<missing>")
    if not isinstance(ga, dict):
        report.fail(f"{gid}: missing or invalid golden_answer object")
        return
    aa = ga.get("accepted_answer")
    if not isinstance(aa, dict) or "value" not in aa:
        report.fail(f"{gid}: accepted_answer missing value")
    mode = ga.get("evidence_mode")
    if mode not in ("all", "any"):
        report.fail(f"{gid}: invalid evidence_mode {mode!r}")
    eids = ga.get("evidence_message_ids") or []
    if not eids:
        report.fail(f"{gid}: empty evidence_message_ids")
    for mid in eids:
        if not isinstance(mid, str) or not MSG_ID_RE.match(mid):
            report.fail(f"{gid}: malformed evidence Message-ID {mid!r}")
            continue
        matches = rows_matching_prompt_bounds(mid, ch, rows_by_mid)
        if not matches:
            packs = sorted(prompt_pack_names(ch.get("prompt", "")))
            scope_hint = f" in packs {packs}" if packs else " in declared scope"
            report.fail(f"{gid}: evidence Message-ID not found in packaged raw mail{scope_hint}: {mid}")


def validate_sources_fragment(sources: dict, difficulty: str, report: Report) -> None:
    if sources.get("difficulty") != difficulty:
        report.fail(f"sources_{difficulty}: difficulty field mismatch")
    expected_prefix = (
        "student_dataset/mail/full_mailboxes/"
        if difficulty == "easy"
        else "student_dataset/mail/packs/"
    )
    for i, src in enumerate(sources.get("sources", [])):
        st = src.get("type")
        packaged_path = src.get("packaged_path", "")
        if not isinstance(packaged_path, str) or not packaged_path.startswith(expected_prefix):
            report.fail(f"sources_{difficulty}[{i}]: packaged_path not in new layout: {packaged_path!r}")
        elif not (REPO_ROOT / packaged_path).is_dir():
            report.fail(f"sources_{difficulty}[{i}]: packaged_path directory does not exist: {packaged_path}")

        if st == "full_mailbox":
            if difficulty != "easy":
                report.fail(f"sources_{difficulty}[{i}]: full_mailbox source outside easy")
            sp = src.get("source_path", "")
            if not sp.startswith(SOURCE_CORPUS_PREFIX):
                report.fail(f"sources_{difficulty}[{i}]: full_mailbox bad source_path {sp!r}")
        elif st in {"bounded_folder", "curated_pack"}:
            if st == "bounded_folder" and difficulty == "hard":
                report.fail(f"sources_{difficulty}[{i}]: hard source cannot be bounded_folder")
            if st == "curated_pack" and difficulty == "easy":
                report.fail(f"sources_{difficulty}[{i}]: easy source cannot be curated_pack")
            sp = src.get("source_path", "")
            if sp and not sp.startswith(SOURCE_CORPUS_PREFIX):
                report.fail(f"sources_{difficulty}[{i}]: bad source_path {sp!r}")
            prov = src.get("source_provenance") or []
            if st == "curated_pack" and not prov:
                report.fail(f"sources_{difficulty}[{i}]: curated_pack {src.get('pack_name')} missing source_provenance")
            for j, p in enumerate(prov):
                psp = p.get("source_path", "")
                if not psp.startswith(SOURCE_CORPUS_PREFIX):
                    report.fail(f"sources_{difficulty}[{i}] provenance[{j}]: bad source_path {psp!r}")
        else:
            report.fail(f"sources_{difficulty}[{i}]: unknown type {st!r}")


def validate_manifest(manifest: dict, report: Report) -> None:
    expected_files = {
        "golden_set": "golden_set/golden_set.json",
    }
    if manifest.get("files") != expected_files:
        report.fail(f"manifest files field mismatch: {manifest.get('files')!r}")
    expected_layout = {"full_mailboxes": "mail/full_mailboxes", "packs": "mail/packs"}
    if manifest.get("mail_layout") != expected_layout:
        report.fail(f"manifest mail_layout mismatch: {manifest.get('mail_layout')!r}")
    if manifest.get("totals", {}).get("emails") != report.counts.get("mail_files_total"):
        report.fail("manifest totals.emails does not match packaged mail files")
    if manifest.get("totals", {}).get("challenges") != report.counts.get("challenges_total"):
        report.fail("manifest totals.challenges does not match golden set records")
    for difficulty in DIFFICULTIES:
        md = manifest.get("difficulties", {}).get(difficulty) or {}
        if md.get("sources_file") != f"manifest/sources_{difficulty}.json":
            report.fail(f"manifest difficulties.{difficulty}.sources_file mismatch")
        if md.get("email_count") != report.counts.get(f"parsed_mail_{difficulty}"):
            report.fail(f"manifest difficulties.{difficulty}.email_count mismatch")
        expected_challenge_total = report.counts.get(f"challenges_{difficulty}")
        total_key = f"{difficulty}_challenges"
        if manifest.get("totals", {}).get(total_key) != expected_challenge_total:
            report.fail(f"manifest totals.{total_key} mismatch")


def main() -> int:
    report = Report()
    validate_layout(report)
    pack_difficulty = build_pack_difficulty_map(report)

    golden_set = load_json(EXPECTED_FILES["golden_set"])
    manifest = load_json(ROOT / "manifest" / "manifest.json")

    if not isinstance(golden_set, list):
        report.fail("golden_set/golden_set.json must be a JSON array")
        golden_set = []

    ch_by_id = index_by_id(golden_set, "golden_set", report)

    if [r.get("id") for r in golden_set] != expected_sort(golden_set):
        report.fail("golden_set/golden_set.json is not sorted by easy, medium, hard, then id")

    challenge_counts = Counter(ch.get("difficulty") for ch in golden_set)
    report.counts["challenges_total"] = len(golden_set)
    report.counts["golden_set_total"] = len(golden_set)
    for difficulty in DIFFICULTIES:
        report.counts[f"challenges_{difficulty}"] = challenge_counts[difficulty]
        expected = EXPECTED_CHALLENGE_COUNTS[difficulty]
        if challenge_counts[difficulty] != expected:
            report.fail(f"{difficulty}: challenge count {challenge_counts[difficulty]} != expected {expected}")

    rows_by_mid = derive_mail_rows(pack_difficulty, report)

    for ch in golden_set:
        validate_challenge(ch, report)
        validate_golden(ch.get("golden_answer"), ch, rows_by_mid, report)

    source_unit_total = 0
    for difficulty in DIFFICULTIES:
        sources = load_json(ROOT / "manifest" / f"sources_{difficulty}.json")
        source_unit_total += len(sources.get("sources", []))
        report.counts[f"sources_units_{difficulty}"] = len(sources.get("sources", []))
        report.counts[f"sources_email_sum_{difficulty}"] = sum_source_email_counts(sources)
        validate_sources_fragment(sources, difficulty, report)
        if report.counts[f"sources_email_sum_{difficulty}"] != report.counts[f"parsed_mail_{difficulty}"]:
            report.fail(
                f"{difficulty}: sources email_count sum {report.counts[f'sources_email_sum_{difficulty}']} "
                f"!= parsed mail files {report.counts[f'parsed_mail_{difficulty}']}"
            )
    report.counts["sources_units_total"] = source_unit_total

    if report.counts["mail_files_total"] != report.counts["parsed_mail_total"]:
        report.fail(
            f"mail file count {report.counts['mail_files_total']} != parsed mail files {report.counts['parsed_mail_total']}"
        )
    if report.counts["mail_full_mailboxes_files"] != report.counts["parsed_mail_easy"]:
        report.fail("mail/full_mailboxes count does not match easy parsed mail files")
    if report.counts["mail_packs_files"] != report.counts["parsed_mail_medium"] + report.counts["parsed_mail_hard"]:
        report.fail("mail/packs count does not match medium+hard parsed mail files")

    medium_001 = ch_by_id.get("medium-001")
    if medium_001:
        pack = next(iter(prompt_pack_names(medium_001.get("prompt", ""))), None)
        pack_rows = [r for rows in rows_by_mid.values() for r in rows if r.get("pack") == pack]
        report.check(f"medium-001 pack {pack!r}: {len(pack_rows)} packaged files")
    hard_duplicates = [mid for mid, rows in rows_by_mid.items() if len(rows) > 1 and any(r.get("difficulty") == "hard" for r in rows)]
    report.check(f"hard duplicate Message-IDs remain distinct by packaged_path/pack: {len(hard_duplicates)} ids")

    validate_manifest(manifest, report)

    print("=" * 60)
    print("GOLDEN DATASET VALIDATION")
    print("=" * 60)
    print(f"Status: {'PASS' if not report.failures else 'FAIL'}")
    print(f"Failures: {len(report.failures)}")
    print(f"Warnings: {len(report.warnings)}")
    print()
    for c in report.checks:
        print(f"  [check] {c}")
    for w in report.warnings:
        print(f"  [warn]  {w}")
    for f in report.failures:
        print(f"  [FAIL]  {f}")
    print()
    print("Counts:", json.dumps(report.counts, indent=2))

    sidecar = ROOT / "validation" / "_validation_result.json"
    with sidecar.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "pass": not report.failures,
                "failures": report.failures,
                "warnings": report.warnings,
                "checks": report.checks,
                "counts": report.counts,
                "manifest": manifest,
            },
            f,
            indent=2,
        )
        f.write("\n")

    return 0 if not report.failures else 1


if __name__ == "__main__":
    sys.exit(main())
