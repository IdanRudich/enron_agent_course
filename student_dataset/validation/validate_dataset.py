#!/usr/bin/env python3
"""Golden Dataset consistency validator for the unified student corpus."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent
DIFFICULTIES = ("easy", "medium", "hard")
DIFFICULTY_ORDER = {difficulty: i for i, difficulty in enumerate(DIFFICULTIES)}

POINT_BANDS = {"easy": (1, 3), "medium": (4, 7), "hard": (8, 10)}
EXPECTED_CHALLENGE_COUNTS = {"easy": 10, "medium": 10, "hard": 8}

EASY_FAMILIES = {
    "exact_email_lookup",
    "message_id_discovery",
    "header_field_extraction",
    "attachment_mention",
    "latest_vs_quoted_sender",
    "date_normalization",
    "recipient_role",
    "body_fact_extraction",
}
MEDIUM_FAMILIES = {
    "bounded_work_summary",
    "search_aggregate",
    "earliest_latest",
    "participant_list",
    "topic_participation",
}
HARD_FAMILIES = {
    "thread_reconstruction",
    "cross_mailbox_corroboration",
    "timeline_synthesis",
    "contradiction_resolution",
}
CROSS_CUTTING = {
    "negative_evidence",
    "forwarded_copy",
    "entity_disambiguation",
    "mailbox_hygiene",
}
ALL_FAMILIES = EASY_FAMILIES | MEDIUM_FAMILIES | HARD_FAMILIES | CROSS_CUTTING

MSG_ID_RE = re.compile(r"^<[^>]+>$")
SOURCE_CORPUS_PREFIX = "enron_mail_20150507/maildir/"
DATASET_MAIL_PREFIX = "student_dataset/mail/"
EXPECTED_FILES = {
    "challenges": ROOT / "challenges" / "challenges.json",
    "golden_answers": ROOT / "golden_answers" / "golden_answers.json",
    "evidence": ROOT / "evidence" / "evidence.jsonl",
}
OBSOLETE_FILES = [
    ROOT / "challenges" / f"challenges_{difficulty}.json"
    for difficulty in DIFFICULTIES
] + [
    ROOT / "golden_answers" / f"golden_{difficulty}.json"
    for difficulty in DIFFICULTIES
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


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{i}: invalid JSON: {e}") from e
    return rows


def count_mail_files(mail_dir: Path) -> int:
    if not mail_dir.is_dir():
        return 0
    return sum(1 for p in mail_dir.rglob("*") if p.is_file() and not p.name.startswith("."))


def dataset_path_exists(packaged_path: str) -> bool:
    return (REPO_ROOT / packaged_path).is_file()


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


def validate_layout(report: Report) -> None:
    for label, path in EXPECTED_FILES.items():
        if not path.is_file():
            report.fail(f"missing unified {label} file: {path.relative_to(ROOT)}")
    for path in OBSOLETE_FILES:
        if path.exists():
            report.fail(f"obsolete per-difficulty file remains: {path.relative_to(ROOT)}")

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


def validate_scope_explicit(challenge: dict, report: Report) -> None:
    cid = challenge.get("id", "<missing>")
    scope = challenge.get("scope")
    if not isinstance(scope, dict):
        report.fail(f"{cid}: missing or invalid scope object")
        return
    prompt = challenge.get("prompt", "")
    if not prompt or not prompt.strip():
        report.fail(f"{cid}: empty prompt")
    mailboxes = scope.get("mailboxes") or []
    folders = scope.get("folders") or []
    packs = scope.get("packs") or []
    topic = scope.get("topic")
    date_range = scope.get("date_range")
    has_bound = bool(mailboxes or folders or packs or topic or date_range)
    search_words = ("search", "count", "how many", "list all", "list every", "earliest", "latest", "who")
    prompt_lower = prompt.lower()
    needs_explicit = any(w in prompt_lower for w in search_words)
    if needs_explicit and not has_bound:
        report.fail(f"{cid}: search-style prompt lacks explicit scope bounds")


def validate_challenge(ch: dict, report: Report) -> None:
    cid = ch.get("id", "<missing>")
    difficulty = ch.get("difficulty")
    if difficulty not in DIFFICULTIES:
        report.fail(f"{cid}: invalid difficulty {difficulty!r}")
        return
    if not isinstance(cid, str) or not cid.startswith(f"{difficulty}-"):
        report.fail(f"{cid}: id prefix does not match difficulty {difficulty!r}")
    family = ch.get("family")
    if family not in ALL_FAMILIES:
        report.fail(f"{cid}: unknown family {family!r}")
    points = ch.get("points")
    lo, hi = POINT_BANDS[difficulty]
    if not isinstance(points, int) or not (lo <= points <= hi):
        report.fail(f"{cid}: points {points!r} outside {difficulty} band {lo}-{hi}")
    es = ch.get("expected_submission") or {}
    if es.get("requires_evidence_message_ids") is not True:
        report.fail(f"{cid}: expected_submission.requires_evidence_message_ids must be true")
    validate_scope_explicit(ch, report)


def rows_matching_challenge_scope(mid: str, challenge: dict, rows_by_mid: dict[str, list[dict]]) -> list[dict]:
    difficulty = challenge.get("difficulty")
    scope = challenge.get("scope") or {}
    packs = set(scope.get("packs") or [])
    rows = [r for r in rows_by_mid.get(mid, []) if r.get("difficulty") == difficulty]
    if packs:
        rows = [r for r in rows if r.get("pack") in packs]
    return rows


def validate_golden(ga: dict, ch: dict | None, rows_by_mid: dict[str, list[dict]], report: Report) -> None:
    gid = ga.get("id", "<missing>")
    if ch is None:
        report.fail(f"{gid}: golden answer has no matching challenge")
        return
    if ga.get("difficulty") != ch.get("difficulty"):
        report.fail(f"{gid}: golden difficulty {ga.get('difficulty')!r} != challenge difficulty {ch.get('difficulty')!r}")
    if ga.get("points") != ch.get("points"):
        report.fail(f"{gid}: points {ga.get('points')} != challenge points {ch.get('points')}")
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
        matches = rows_matching_challenge_scope(mid, ch, rows_by_mid)
        if not matches:
            packs = ch.get("scope", {}).get("packs") or []
            scope_hint = f" in packs {packs}" if packs else ""
            report.fail(f"{gid}: evidence Message-ID not in {ch.get('difficulty')} evidence{scope_hint}: {mid}")


def validate_evidence_rows(rows: list[dict], report: Report) -> dict[str, list[dict]]:
    rows_by_mid: dict[str, list[dict]] = defaultdict(list)
    identity_counts: Counter[tuple[str, str, str | None]] = Counter()
    difficulty_counts: Counter[str] = Counter()

    for i, row in enumerate(rows, 1):
        mid = row.get("message_id")
        difficulty = row.get("difficulty")
        if difficulty not in DIFFICULTIES:
            report.fail(f"evidence line {i}: invalid difficulty {difficulty!r}")
        else:
            difficulty_counts[difficulty] += 1
        if not isinstance(mid, str) or not MSG_ID_RE.match(mid):
            report.fail(f"evidence line {i}: bad message_id {mid!r}")
        else:
            rows_by_mid[mid].append(row)
        sp = row.get("source_path", "")
        if not isinstance(sp, str) or not sp.startswith(SOURCE_CORPUS_PREFIX):
            report.fail(f"evidence line {i} {mid}: source_path missing maildir lineage: {sp!r}")
        pp = row.get("packaged_path", "")
        if not isinstance(pp, str) or not pp.startswith(DATASET_MAIL_PREFIX):
            report.fail(f"evidence line {i} {mid}: bad packaged_path {pp!r}")
        elif difficulty == "easy" and not pp.startswith("student_dataset/mail/full_mailboxes/"):
            report.fail(f"evidence line {i} {mid}: easy evidence must live under mail/full_mailboxes: {pp}")
        elif difficulty in ("medium", "hard") and not pp.startswith("student_dataset/mail/packs/"):
            report.fail(f"evidence line {i} {mid}: {difficulty} evidence must live under mail/packs: {pp}")
        if pp and not dataset_path_exists(pp):
            report.fail(f"evidence line {i} {mid}: packaged_path does not exist: {pp}")
        if difficulty == "easy" and row.get("pack") is not None:
            report.fail(f"evidence line {i} {mid}: easy full mailbox row should have pack=null")
        if difficulty in ("medium", "hard") and not row.get("pack"):
            report.fail(f"evidence line {i} {mid}: {difficulty} pack row missing pack")
        identity_counts[(mid, pp, row.get("pack"))] += 1

    for identity, count in identity_counts.items():
        if count > 1:
            report.fail(f"duplicate evidence identity {identity}: {count} rows")

    duplicate_mids = sum(1 for mid_rows in rows_by_mid.values() if len(mid_rows) > 1)
    report.counts["evidence_total"] = len(rows)
    for difficulty in DIFFICULTIES:
        report.counts[f"evidence_{difficulty}"] = difficulty_counts[difficulty]
    report.counts["duplicate_message_ids_allowed"] = duplicate_mids
    report.check(
        "unified evidence: "
        f"{len(rows)} rows, {duplicate_mids} Message-IDs appear in multiple packaged paths/packs"
    )
    return rows_by_mid


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
        "challenges": "challenges/challenges.json",
        "golden_answers": "golden_answers/golden_answers.json",
        "evidence": "evidence/evidence.jsonl",
    }
    if manifest.get("files") != expected_files:
        report.fail(f"manifest files field mismatch: {manifest.get('files')!r}")
    expected_layout = {"full_mailboxes": "mail/full_mailboxes", "packs": "mail/packs"}
    if manifest.get("mail_layout") != expected_layout:
        report.fail(f"manifest mail_layout mismatch: {manifest.get('mail_layout')!r}")
    if manifest.get("totals", {}).get("emails") != report.counts.get("evidence_total"):
        report.fail("manifest totals.emails does not match unified evidence rows")
    if manifest.get("totals", {}).get("challenges") != report.counts.get("challenges_total"):
        report.fail("manifest totals.challenges does not match unified challenges")
    for difficulty in DIFFICULTIES:
        md = manifest.get("difficulties", {}).get(difficulty) or {}
        if md.get("sources_file") != f"manifest/sources_{difficulty}.json":
            report.fail(f"manifest difficulties.{difficulty}.sources_file mismatch")
        if md.get("email_count") != report.counts.get(f"evidence_{difficulty}"):
            report.fail(f"manifest difficulties.{difficulty}.email_count mismatch")
        expected_challenge_total = report.counts.get(f"challenges_{difficulty}")
        total_key = f"{difficulty}_challenges"
        if manifest.get("totals", {}).get(total_key) != expected_challenge_total:
            report.fail(f"manifest totals.{total_key} mismatch")


def main() -> int:
    report = Report()
    validate_layout(report)

    challenges = load_json(EXPECTED_FILES["challenges"])
    golden = load_json(EXPECTED_FILES["golden_answers"])
    evidence_rows = load_jsonl(EXPECTED_FILES["evidence"])
    manifest = load_json(ROOT / "manifest" / "manifest.json")

    if not isinstance(challenges, list):
        report.fail("challenges/challenges.json must be a JSON array")
        challenges = []
    if not isinstance(golden, list):
        report.fail("golden_answers/golden_answers.json must be a JSON array")
        golden = []

    ch_by_id = index_by_id(challenges, "challenges", report)
    ga_by_id = index_by_id(golden, "golden_answers", report)
    ch_ids = set(ch_by_id)
    ga_ids = set(ga_by_id)
    if ch_ids != ga_ids:
        if ch_ids - ga_ids:
            report.fail(f"challenges without golden: {sorted(ch_ids - ga_ids)}")
        if ga_ids - ch_ids:
            report.fail(f"golden without challenges: {sorted(ga_ids - ch_ids)}")

    if [r.get("id") for r in challenges] != expected_sort(challenges):
        report.fail("challenges/challenges.json is not sorted by easy, medium, hard, then id")
    if [r.get("id") for r in golden] != expected_sort(golden):
        report.fail("golden_answers/golden_answers.json is not sorted by easy, medium, hard, then id")

    challenge_counts = Counter(ch.get("difficulty") for ch in challenges)
    golden_counts = Counter(ga.get("difficulty") for ga in golden)
    report.counts["challenges_total"] = len(challenges)
    report.counts["golden_total"] = len(golden)
    for difficulty in DIFFICULTIES:
        report.counts[f"challenges_{difficulty}"] = challenge_counts[difficulty]
        report.counts[f"golden_{difficulty}"] = golden_counts[difficulty]
        expected = EXPECTED_CHALLENGE_COUNTS[difficulty]
        if challenge_counts[difficulty] != expected:
            report.fail(f"{difficulty}: challenge count {challenge_counts[difficulty]} != expected {expected}")
        if golden_counts[difficulty] != challenge_counts[difficulty]:
            report.fail(f"{difficulty}: golden count {golden_counts[difficulty]} != challenge count {challenge_counts[difficulty]}")

    rows_by_mid = validate_evidence_rows(evidence_rows, report)

    for ch in challenges:
        validate_challenge(ch, report)
    for ga in golden:
        validate_golden(ga, ch_by_id.get(ga.get("id")), rows_by_mid, report)

    source_unit_total = 0
    for difficulty in DIFFICULTIES:
        sources = load_json(ROOT / "manifest" / f"sources_{difficulty}.json")
        source_unit_total += len(sources.get("sources", []))
        report.counts[f"sources_units_{difficulty}"] = len(sources.get("sources", []))
        report.counts[f"sources_email_sum_{difficulty}"] = sum_source_email_counts(sources)
        validate_sources_fragment(sources, difficulty, report)
        if report.counts[f"sources_email_sum_{difficulty}"] != report.counts[f"evidence_{difficulty}"]:
            report.fail(
                f"{difficulty}: sources email_count sum {report.counts[f'sources_email_sum_{difficulty}']} "
                f"!= evidence rows {report.counts[f'evidence_{difficulty}']}"
            )
    report.counts["sources_units_total"] = source_unit_total

    if report.counts["mail_files_total"] != report.counts["evidence_total"]:
        report.fail(
            f"mail file count {report.counts['mail_files_total']} != evidence rows {report.counts['evidence_total']}"
        )
    if report.counts["mail_full_mailboxes_files"] != report.counts["evidence_easy"]:
        report.fail("mail/full_mailboxes count does not match easy evidence rows")
    if report.counts["mail_packs_files"] != report.counts["evidence_medium"] + report.counts["evidence_hard"]:
        report.fail("mail/packs count does not match medium+hard evidence rows")

    # Spot checks for documented scope and duplicated Message-ID behavior.
    medium_001 = ch_by_id.get("medium-001")
    if medium_001:
        pack = (medium_001.get("scope", {}).get("packs") or [None])[0]
        pack_rows = [r for r in evidence_rows if r.get("pack") == pack]
        report.check(f"medium-001 pack {pack!r}: {len(pack_rows)} evidence rows")
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
