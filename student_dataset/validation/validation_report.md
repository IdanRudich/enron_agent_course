# Golden Dataset Validation Report

## Summary

**Status: PASS**

Validation completed on **2026-07-09** against the unified student-facing corpus contract in `DATASET_CONTRACT.md` and the value-matching rules in `NORMALIZATION.md`.

| Metric | Easy | Medium | Hard | Total |
| --- | ---: | ---: | ---: | ---: |
| Packaged emails | 1,329 | 1,500 | 63 | **2,892** |
| Golden Set records | 10 | 10 | 8 | **28** |
| Source units | 5 full mailboxes | 21 bounded folders | 6 curated packs | 32 |

Dataset remains under the 6,000 email ceiling (`target_email_ceiling`).

---

## Final Structure Validated

```
student_dataset/
  mail/
    full_mailboxes/          # 1,329 files from Easy full mailboxes
    packs/                   # 1,563 files from Medium + Hard packs
  golden_set/golden_set.json
  manifest/manifest.json
  manifest/sources_easy.json
  manifest/sources_medium.json
  manifest/sources_hard.json
```

The old physical split (`mail/easy`, `mail/medium`, `mail/hard`) and old split public challenge / answer files were removed. No prebuilt evidence index is shipped; students may build their own from raw mail. Difficulty is retained as metadata on Golden Set records, source fragments, and manifest counts.

---

## Checks Performed

- [x] **Unified file presence** - `golden_set/golden_set.json` exists.
- [x] **No shipped evidence index** - no prebuilt evidence index remains in the student package.
- [x] **Obsolete file removal** - no split challenge, split golden-answer, per-difficulty, or evidence files remain.
- [x] **Mail layout** - `mail/full_mailboxes` and `mail/packs` exist; `mail/easy`, `mail/medium`, and `mail/hard` do not.
- [x] **Golden Set shape** - all 28 records contain public challenge fields plus a nested `golden_answer` object, without routing-only `family` or `scope` fields.
- [x] **Point bands** - easy 1-3, medium 4-7, hard 8-10.
- [x] **Golden Set sort order** - unified array sorted by Easy, Medium, Hard, then id.
- [x] **Evidence Message-ID resolution** - all nested `golden_answer.evidence_message_ids` resolve by parsing `Message-ID:` headers from prompt-bounded packaged raw mail files.
- [x] **Source lineage** - all source fragments trace back under `enron_mail_20150507/maildir/`.
- [x] **Source count reconciliation** - source fragment `email_count` sums match packaged mail files by difficulty.
- [x] **Mail count reconciliation** - mail files on disk = 2,892.
- [x] **Manifest consistency** - `manifest.json` points to the unified files and reports matching totals.
- [x] **Duplicate Message-ID handling** - duplicate Message-IDs intentionally appear in multiple packaged paths/packs; validation preserves path and pack context while parsing raw mail.

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
parsed mail: 2892 files with Message-ID headers
medium-001 pack 'symes-k__power_marketer': 136 packaged files
duplicate Message-IDs remain distinct by packaged_path/pack context
```

---

## Notes and Choices

- The old question-only `challenges/challenges.json` and separate `golden_answers/golden_answers.json` files were removed because the docs and validator now enforce the single Golden Set contract.
- The unified generated evidence index was removed from the student package. Students can build an index themselves as part of the challenge.
- `manifest/sources_easy.json`, `manifest/sources_medium.json`, and `manifest/sources_hard.json` were kept as provenance fragments and updated to the new `packaged_path` layout.
- The `easy-004` fix was preserved: its golden answer uses Message-ID `<14464692.1075840045536.JavaMail.evans@thyme>` and subject `Confirmation of Interview on Friday with Tim Belden`.
- The validator no longer rewrites `manifest.json`; it validates manifest counts and writes only `validation/_validation_result.json` as its machine-readable sidecar.

No remaining structural validation issues are known.
