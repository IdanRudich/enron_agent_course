# Golden Dataset Validation Report

## Summary (pass/fail, totals)

**Status: PASS**

Validation completed on **2026-07-08** against `DATASET_CONTRACT.md` and `NORMALIZATION.md`. All automated consistency checks passed after adjusting the validator to exclude placeholder `.gitkeep` files from mail-on-disk counts (see Fixes below). No challenge, golden-answer, evidence, or source-fragment data edits were required.

| Metric | Easy | Medium | Hard | Total |
| --- | ---: | ---: | ---: | ---: |
| Packaged emails | 1,329 | 1,500 | 63 | **2,892** |
| Challenge Questions | 10 | 10 | 8 | **28** |
| Golden Answers | 10 | 10 | 8 | **28** |
| Source units | 5 mailboxes | 21 bounded folders | 6 curated packs | 32 |

Dataset is well under the 6,000 email ceiling (`target_email_ceiling`).

---

## Checks performed (checklist with counts)

- [x] **Challenge ↔ Golden Answer id alignment** — 28/28 pairs matched by id across easy, medium, hard.
- [x] **Points equality** — every golden answer `points` equals its challenge `points` (28/28).
- [x] **Point bands** — easy 1–3 (10/10), medium 4–7 (10/10), hard 8–10 (8/8).
- [x] **Evidence Message-ID resolution** — all `evidence_message_ids` in golden answers resolve in the matching `evidence_<difficulty>.jsonl` (0 missing).
- [x] **Message-ID canonical form** — all referenced ids use angle-bracket form `<...@...>`.
- [x] **`requires_evidence_message_ids`** — true on all 28 challenges.
- [x] **Challenge families** — all values from pinned taxonomy; full family coverage per difficulty:
  - Easy: 8/8 families (10 challenges)
  - Medium: 5/5 families (10 challenges)
  - Hard: 4/4 families (8 challenges)
- [x] **Challenge record completeness** — every challenge has `difficulty`, `points`, non-empty `prompt`, and `scope` object.
- [x] **Search-scope explicitness** — search/aggregate prompts declare bounds via `scope.mailboxes`, `scope.folders`, `scope.packs`, `scope.topic`, or `scope.date_range`.
- [x] **Evidence index lineage** — 2,892/2,892 evidence rows have `source_path` under `enron_mail_20150507/maildir/`.
- [x] **Sources fragment lineage** — all `full_mailbox`, `bounded_folder`, and `curated_pack` records trace to raw maildir; hard curated packs include `source_provenance` arrays (6/6 packs).
- [x] **Email count reconciliation**:
  - Evidence JSONL line counts = sources fragment `email_count` sums = mail files on disk (excluding `.gitkeep`) for each difficulty.
- [x] **Medium spot-check** — `medium-001` scope (`symes-k` / `power_marketer` / pack `symes-k__power_marketer`) matches **136** evidence rows for that pack.
- [x] **Manifest aggregation** — `manifest/manifest.json` updated with `created: 2026-07-08` and final counts.

Validator: `student_dataset/validation/validate_dataset.py` (stdlib only).

---

## Failures found and fixes applied

### Initial run (3 failures)

Disk mail-file counts exceeded evidence line counts by 1 per difficulty:

| Difficulty | Evidence lines | Mail files (raw) | Delta |
| --- | ---: | ---: | ---: |
| easy | 1,329 | 1,330 | +1 |
| medium | 1,500 | 1,501 | +1 |
| hard | 63 | 64 | +1 |

**Root cause:** placeholder `mail/<difficulty>/.gitkeep` files (not emails, not in evidence index).

**Fix applied:** updated `validate_dataset.py` `count_mail_files()` to skip `.gitkeep`. Re-run → **0 failures**. No packaged email or JSON artifact edits.

**Manifest note:** the first (failed) run briefly wrote inflated counts including `.gitkeep`; the passing re-run corrected `manifest.json` to evidence-aligned totals.

### Dataset content fixes

**None.** Challenge, golden-answer, evidence, and source fragments were already internally consistent.

---

## Remaining known issues / grading softness

1. **`bounded_work_summary` (medium-007, medium-008)** — summary/naming answers accept listed aliases and case/punctuation-insensitive matches; `evidence_mode: "any"` allows any representative in-pack Message-ID, not only the cited example. Intentional per `grading_notes`.
2. **`medium-007` dominance threshold** — golden answer cites "99 of 136" Daily Power Report subjects; graders should treat this as documented fact, not re-derive the count at grade time.
3. **Easy mailbox naming** — `sources_easy.json` documents that `slinger-r` owner is Ryan Slinger (`ryan.slinger@enron.com`), not the illustrative `richard.slinger@enron.com` in `DATASET_CONTRACT.md` examples.
4. **Parser pitfalls** — several mailboxes/folders flag double-dot addresses, empty `To:` on bulletins, and `contacts` folders; challenges already scope around these where relevant.

No unfixable structural issues remain.

---

## Manifest aggregation (final counts table)

| Field | Value |
| --- | --- |
| `dataset_name` | Beginner Enron Golden Dataset |
| `dataset_version` | 0.1.0 |
| `created` | 2026-07-08 |
| `source_corpus` | enron_mail_20150507 |
| `target_email_ceiling` | 6,000 |
| **easy `email_count`** | 1,329 |
| **medium `email_count`** | 1,500 |
| **hard `email_count`** | 63 |
| **`totals.emails`** | **2,892** |
| **`totals.challenges`** | **28** |
| `totals.easy_challenges` | 10 |
| `totals.medium_challenges` | 10 |
| `totals.hard_challenges` | 8 |

Source fragments: `manifest/sources_easy.json` (5 units), `manifest/sources_medium.json` (21 units), `manifest/sources_hard.json` (6 units).
