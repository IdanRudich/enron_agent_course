#!/usr/bin/env python3
"""One-off Golden Dataset consistency validator (Ticket 8). Stdlib only."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIFFICULTIES = ("easy", "medium", "hard")

POINT_BANDS = {"easy": (1, 3), "medium": (4, 7), "hard": (8, 10)}

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


@dataclass
class Report:
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)
    fixes: list[str] = field(default_factory=list)
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
    return sum(
        1
        for p in mail_dir.rglob("*")
        if p.is_file() and p.name != ".gitkeep"
    )


def sum_source_email_counts(sources: dict) -> int:
    return sum(s.get("email_count", 0) for s in sources.get("sources", []))


def index_by_id(records: list[dict]) -> dict[str, dict]:
    out = {}
    for r in records:
        out[r["id"]] = r
    return out


def validate_scope_explicit(challenge: dict, report: Report) -> None:
    cid = challenge["id"]
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
    search_words = ("search", "count", "how many", "list all", "earliest", "latest", "who")
    prompt_lower = prompt.lower()
    needs_explicit = any(w in prompt_lower for w in search_words)
    if needs_explicit and not has_bound:
        report.fail(f"{cid}: search-style prompt lacks explicit scope bounds")


def validate_challenge(ch: dict, difficulty: str, report: Report) -> None:
    cid = ch.get("id", "<missing>")
    if ch.get("difficulty") != difficulty:
        report.fail(f"{cid}: difficulty {ch.get('difficulty')!r} != file difficulty {difficulty!r}")
    family = ch.get("family")
    if family not in ALL_FAMILIES:
        report.fail(f"{cid}: unknown family {family!r}")
    points = ch.get("points")
    lo, hi = POINT_BANDS[difficulty]
    if not isinstance(points, int) or not (lo <= points <= hi):
        report.fail(f"{cid}: points {points!r} outside band {lo}-{hi}")
    es = ch.get("expected_submission") or {}
    if es.get("requires_evidence_message_ids") is not True:
        report.fail(f"{cid}: expected_submission.requires_evidence_message_ids must be true")
    validate_scope_explicit(ch, report)


def validate_golden(ga: dict, difficulty: str, ch: dict | None, evidence_ids: set[str], report: Report) -> None:
    gid = ga.get("id", "<missing>")
    if ch is None:
        report.fail(f"{gid}: golden answer has no matching challenge")
        return
    if ga.get("difficulty") != difficulty:
        report.fail(f"{gid}: golden difficulty mismatch")
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
        elif mid not in evidence_ids:
            report.fail(f"{gid}: evidence Message-ID not in index: {mid}")


def validate_evidence_row(row: dict, difficulty: str, report: Report) -> None:
    mid = row.get("message_id")
    if not mid or not MSG_ID_RE.match(mid):
        report.fail(f"evidence_{difficulty}: bad message_id {mid!r}")
    sp = row.get("source_path", "")
    if not sp.startswith(SOURCE_CORPUS_PREFIX):
        report.fail(f"evidence_{difficulty} {mid}: source_path missing maildir lineage: {sp!r}")
    pp = row.get("packaged_path", "")
    if not pp.startswith("student_dataset/mail/"):
        report.fail(f"evidence_{difficulty} {mid}: bad packaged_path {pp!r}")


def validate_sources_fragment(sources: dict, difficulty: str, report: Report) -> None:
    if sources.get("difficulty") != difficulty:
        report.fail(f"sources_{difficulty}: difficulty field mismatch")
    for i, src in enumerate(sources.get("sources", [])):
        st = src.get("type")
        sp = src.get("source_path", "")
        if st == "full_mailbox":
            if not sp.startswith(SOURCE_CORPUS_PREFIX):
                report.fail(f"sources_{difficulty}[{i}]: full_mailbox bad source_path {sp!r}")
        elif st == "bounded_folder":
            if not sp.startswith(SOURCE_CORPUS_PREFIX):
                report.fail(f"sources_{difficulty}[{i}]: bounded_folder bad source_path {sp!r}")
        elif st == "curated_pack":
            prov = src.get("source_provenance") or []
            if not prov:
                report.fail(f"sources_{difficulty}[{i}]: curated_pack {src.get('pack_name')} missing source_provenance")
            for j, p in enumerate(prov):
                psp = p.get("source_path", "")
                if not psp.startswith(SOURCE_CORPUS_PREFIX):
                    report.fail(
                        f"sources_{difficulty}[{i}] provenance[{j}]: bad source_path {psp!r}"
                    )
        else:
            report.fail(f"sources_{difficulty}[{i}]: unknown type {st!r}")


def spot_check_medium_pack(evidence_rows: list[dict], pack_name: str, report: Report) -> None:
    pack_rows = [r for r in evidence_rows if r.get("pack") == pack_name]
    report.check(f"medium spot-check pack {pack_name!r}: {len(pack_rows)} evidence rows")


def build_manifest(counts: dict) -> dict:
    manifest = load_json(ROOT / "manifest" / "manifest.json")
    manifest["created"] = date.today().isoformat()
    for diff in DIFFICULTIES:
        manifest["difficulties"][diff]["email_count"] = counts[f"email_disk_{diff}"]
    manifest["totals"] = {
        "emails": counts["email_disk_total"],
        "challenges": counts["challenges_total"],
        "easy_challenges": counts["challenges_easy"],
        "medium_challenges": counts["challenges_medium"],
        "hard_challenges": counts["challenges_hard"],
    }
    return manifest


def main() -> int:
    report = Report()

    all_challenge_ids: dict[str, str] = {}
    evidence_by_diff: dict[str, list[dict]] = {}
    evidence_id_sets: dict[str, set[str]] = {}

    for diff in DIFFICULTIES:
        challenges = load_json(ROOT / "challenges" / f"challenges_{diff}.json")
        golden = load_json(ROOT / "golden_answers" / f"golden_{diff}.json")
        evidence_rows = load_jsonl(ROOT / "evidence" / f"evidence_{diff}.jsonl")
        sources = load_json(ROOT / "manifest" / f"sources_{diff}.json")

        evidence_by_diff[diff] = evidence_rows
        evidence_id_sets[diff] = {r["message_id"] for r in evidence_rows if "message_id" in r}

        ch_by_id = index_by_id(challenges)
        ga_by_id = index_by_id(golden)

        report.counts[f"challenges_{diff}"] = len(challenges)
        report.counts[f"golden_{diff}"] = len(golden)
        report.counts[f"evidence_{diff}"] = len(evidence_rows)
        report.counts[f"sources_email_sum_{diff}"] = sum_source_email_counts(sources)

        disk_count = count_mail_files(ROOT / "mail" / diff)
        report.counts[f"email_disk_{diff}"] = disk_count

        report.check(
            f"{diff}: {len(challenges)} challenges, {len(golden)} golden answers, "
            f"{len(evidence_rows)} evidence lines, {disk_count} mail files, "
            f"sources sum email_count={report.counts[f'sources_email_sum_{diff}']}"
        )

        if len(challenges) != len(golden):
            report.fail(f"{diff}: challenge count {len(challenges)} != golden count {len(golden)}")

        ch_ids = set(ch_by_id)
        ga_ids = set(ga_by_id)
        if ch_ids != ga_ids:
            only_ch = ch_ids - ga_ids
            only_ga = ga_ids - ch_ids
            if only_ch:
                report.fail(f"{diff}: challenges without golden: {sorted(only_ch)}")
            if only_ga:
                report.fail(f"{diff}: golden without challenges: {sorted(only_ga)}")

        for cid, ch in ch_by_id.items():
            if cid in all_challenge_ids:
                report.fail(f"{cid}: duplicate id across difficulties (also in {all_challenge_ids[cid]})")
            all_challenge_ids[cid] = diff
            validate_challenge(ch, diff, report)

        for gid, ga in ga_by_id.items():
            validate_golden(ga, diff, ch_by_id.get(gid), evidence_id_sets[diff], report)

        for row in evidence_rows:
            validate_evidence_row(row, diff, report)

        validate_sources_fragment(sources, diff, report)

        if disk_count != len(evidence_rows):
            report.fail(
                f"{diff}: disk mail file count {disk_count} != evidence lines {len(evidence_rows)}"
            )
        if report.counts[f"sources_email_sum_{diff}"] != len(evidence_rows):
            report.warn(
                f"{diff}: sources email_count sum {report.counts[f'sources_email_sum_{diff}']} "
                f"!= evidence lines {len(evidence_rows)}"
            )

    report.counts["challenges_total"] = sum(report.counts[f"challenges_{d}"] for d in DIFFICULTIES)
    report.counts["email_disk_total"] = sum(report.counts[f"email_disk_{d}"] for d in DIFFICULTIES)

    # Spot-check first medium bounded folder / pack from medium-001 scope if present
    medium_ch = load_json(ROOT / "challenges" / "challenges_medium.json")
    m001 = next((c for c in medium_ch if c["id"] == "medium-001"), None)
    if m001:
        packs = m001.get("scope", {}).get("packs") or []
        if packs:
            spot_check_medium_pack(evidence_by_diff["medium"], packs[0], report)
        folders = m001.get("scope", {}).get("folders") or []
        mailboxes = m001.get("scope", {}).get("mailboxes") or []
        if mailboxes and folders:
            mb, fo = mailboxes[0], folders[0]
            scoped = [
                r
                for r in evidence_by_diff["medium"]
                if r.get("source_mailbox") == mb and r.get("source_folder") == fo
            ]
            report.check(f"medium-001 scope {mb}/{fo}: {len(scoped)} evidence rows")

    # Hard curated pack lineage: every evidence row with pack set must have source_path
    hard_pack_rows = [r for r in evidence_by_diff["hard"] if r.get("pack")]
    report.check(f"hard curated pack emails: {len(hard_pack_rows)} rows with pack set")

    manifest = build_manifest(report.counts)
    manifest_path = ROOT / "manifest" / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    report.check(f"manifest.json updated (created={manifest['created']})")

    # Print summary for CLI
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

    # Write machine-readable sidecar for report generation
    sidecar = ROOT / "validation" / "_validation_result.json"
    with sidecar.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "pass": not report.failures,
                "failures": report.failures,
                "warnings": report.warnings,
                "checks": report.checks,
                "fixes": report.fixes,
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
