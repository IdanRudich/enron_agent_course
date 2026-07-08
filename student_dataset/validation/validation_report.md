# Golden Dataset Validation Report

## Summary

**Status: PASS**

Validation completed on **2026-07-09** against the unified student-facing corpus contract in `DATASET_CONTRACT.md` and the value-matching rules in `NORMALIZATION.md`.

| Metric | Easy | Medium | Hard | Total |
| --- | ---: | ---: | ---: | ---: |
| Packaged emails | 1,329 | 1,500 | 63 | **2,892** |
| Challenge Questions | 10 | 10 | 8 | **28** |
| Golden Answers | 10 | 10 | 8 | **28** |
| Source units | 5 full mailboxes | 21 bounded folders | 6 curated packs | 32 |

Dataset remains under the 6,000 email ceiling (`target_email_ceiling`).

---

## Final Structure Validated

```
student_dataset/
  mail/
    full_mailboxes/          # 1,329 files from Easy full mailboxes
    packs/                   # 1,563 files from Medium + Hard packs
  challenges/challenges.json
  golden_answers/golden_answers.json
  evidence/evidence.jsonl
  manifest/manifest.json
  manifest/sources_easy.json
  manifest/sources_medium.json
  manifest/sources_hard.json
```

The old physical split (`mail/easy`, `mail/medium`, `mail/hard`) and old per-difficulty public index files were removed. Difficulty is retained as metadata on Challenge Questions, Golden Answers, evidence rows, source fragments, and manifest counts.

---

## Checks Performed

- [x] **Unified file presence** - `challenges/challenges.json`, `golden_answers/golden_answers.json`, and `evidence/evidence.jsonl` exist.
- [x] **Obsolete file removal** - no `challenges_<difficulty>.json`, `golden_<difficulty>.json`, or `evidence_<difficulty>.jsonl` files remain.
- [x] **Mail layout** - `mail/full_mailboxes` and `mail/packs` exist; `mail/easy`, `mail/medium`, and `mail/hard` do not.
- [x] **Challenge to Golden Answer id alignment** - 28/28 pairs matched by id.
- [x] **Points equality** - every golden answer `points` equals its challenge `points`.
- [x] **Point bands** - easy 1-3, medium 4-7, hard 8-10.
- [x] **Challenge sort order** - unified challenge array sorted by Easy, Medium, Hard, then id.
- [x] **Golden sort order** - unified golden-answer array sorted the same way.
- [x] **Evidence Message-ID resolution** - all `evidence_message_ids` in golden answers resolve in `evidence/evidence.jsonl` for the matching difficulty and scoped pack when applicable.
- [x] **Evidence row difficulty** - all 2,892 evidence rows include `difficulty` with one of `easy`, `medium`, or `hard`.
- [x] **Packaged path existence** - every evidence `packaged_path` points to an existing packaged email file.
- [x] **Source lineage** - all evidence rows and source fragments trace back under `enron_mail_20150507/maildir/`.
- [x] **Source count reconciliation** - source fragment `email_count` sums match evidence rows by difficulty.
- [x] **Mail count reconciliation** - mail files on disk = evidence JSONL rows = 2,892.
- [x] **Manifest consistency** - `manifest.json` points to the unified files and reports matching totals.
- [x] **Duplicate Message-ID handling** - 17 Message-IDs intentionally appear in multiple packaged paths/packs; each evidence row remains distinct by `(message_id, packaged_path, pack)`.

Validator: `student_dataset/validation/validate_dataset.py` (stdlib only).

---

## Command Run

```bash
python3 student_dataset/validation/validate_dataset.py
```

Result: **PASS** with 0 failures and 0 warnings.

Key output:

```text
mail layout: 1329 full-mailbox files, 1563 pack files
unified evidence: 2892 rows, 17 Message-IDs appear in multiple packaged paths/packs
medium-001 pack 'symes-k__power_marketer': 136 evidence rows
hard duplicate Message-IDs remain distinct by packaged_path/pack: 17 ids
```

---

## Notes and Choices

- The old per-difficulty challenge, golden-answer, and evidence files were removed because the docs and validator now enforce the unified contract.
- `manifest/sources_easy.json`, `manifest/sources_medium.json`, and `manifest/sources_hard.json` were kept as provenance fragments and updated to the new `packaged_path` layout.
- The `easy-004` fix was preserved: its golden answer uses Message-ID `<14464692.1075840045536.JavaMail.evans@thyme>` and subject `Confirmation of Interview on Friday with Tim Belden`.
- The validator no longer rewrites `manifest.json`; it validates manifest counts and writes only `validation/_validation_result.json` as its machine-readable sidecar.

No remaining structural validation issues are known.
