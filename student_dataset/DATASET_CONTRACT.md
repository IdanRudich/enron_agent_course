# Dataset Contract - Beginner Enron Golden Dataset

This document is the **authoritative contract** for the Beginner Enron Golden Dataset artifact. Every downstream consumer should follow the directory layout, record shapes, and rules defined here. When this document and any other note disagree, this document wins for structure/schemas and `NORMALIZATION.md` wins for value-matching rules.

The artifact is **plain data**: JSON, Markdown, and copied raw email files. It is not tied to any implementation package, framework, or language.

---

## 1. Directory Layout

```
student_dataset/
  DATASET_CONTRACT.md
  NORMALIZATION.md
  manifest/
    manifest.json
    sources_easy.json
    sources_medium.json
    sources_hard.json
  mail/
    full_mailboxes/
      <mailbox>/<folder>/<n>.
    packs/
      <pack_name>/<n>.
      <pack_name>/<mailbox>__<folder>__<n>.
  golden_set/
    golden_set.json
  validation/
    validate_dataset.py
    validation_report.md
```

### What Lives Where

| Location | Contents |
| --- | --- |
| `mail/full_mailboxes/<mailbox>/<folder>/<n>.` | Full beginner-friendly mailboxes, native Enron folder structure preserved. |
| `mail/packs/<pack_name>/...` | Medium bounded folders and Hard curated multi-message packs. |
| `golden_set/golden_set.json` | Public Golden Set as one JSON array, sorted by difficulty order Easy, Medium, Hard, then `id`. Each record contains the challenge question fields plus its nested student-visible Golden Answer. |
| `manifest/sources_<difficulty>.json` | Per-difficulty source selection fragments. These document source provenance and email counts; they do not imply separate student mail corpora. |
| `manifest/manifest.json` | Top-level manifest: version, unified files, mail layout, counts, and provenance. |
| `validation/validation_report.md` | Consistency report produced during verification. |

The physical student corpus is unified. Difficulty remains explicit metadata on Golden Set records, source fragments, and manifest counts. The package intentionally does not ship a prebuilt Message-ID index; students may build one from the raw mail files.

---

## 2. Golden Set Record

Element of the JSON array in `golden_set/golden_set.json`.

### Fields

| Field | Type | Description |
| --- | --- | --- |
| `id` | string | Stable challenge id, `"<difficulty>-NNN"` zero-padded to 3 digits, e.g. `"easy-001"`. Unique across the whole dataset. |
| `difficulty` | string | One of `"easy"`, `"medium"`, `"hard"`. Difficulty is challenge metadata and determines the point band. |
| `family` | string | Challenge family; must be one of the values in [Challenge Families](#3-challenge-families). |
| `points` | integer | Fixed Challenge Points. Must fit the difficulty's Point Band. |
| `prompt` | string | Beginner-friendly task text. Must state scope explicitly whenever search is required. |
| `scope` | object | Where the answer may be found. See below. |
| `expected_submission` | object | What a valid student submission must contain. See below. |
| `golden_answer` | object | The official student-visible answer and accepted evidence for this challenge. See [Golden Answer Object](#4-golden-answer-object). |

`scope` object:

| Field | Type | Description |
| --- | --- | --- |
| `mailboxes` | array of string | In-bounds mailbox names, or `[]` if not scoped by mailbox. |
| `folders` | array of string | In-bounds folder names, or `[]`. |
| `packs` | array of string | In-bounds pack names under `mail/packs/`, or `[]`. |
| `date_range` | object or null | `null`, or `{ "start": "<ISO 8601>", "end": "<ISO 8601>" }` inclusive. |
| `topic` | string or null | Free-text topic label for topic-bounded challenges, else `null`. |

`expected_submission` object:

| Field | Type | Description |
| --- | --- | --- |
| `answer_format` | string | Short description of the expected answer shape. |
| `requires_evidence_message_ids` | boolean | Whether the student must cite Evidence Message-IDs. This release uses `true` for every challenge. |

### Example

```json
{
  "id": "easy-001",
  "difficulty": "easy",
  "family": "exact_email_lookup",
  "points": 2,
  "prompt": "Open the email with Message-ID <example123@enron.com> in the slinger-r inbox. Who is listed as the sender (From)?",
  "scope": {"mailboxes": ["slinger-r"], "folders": ["inbox"], "packs": [], "date_range": null, "topic": null},
  "expected_submission": {"answer_format": "single email address", "requires_evidence_message_ids": true},
  "golden_answer": {
    "accepted_answer": {"value": "sender@example.com", "aliases": []},
    "evidence_message_ids": ["<example123@enron.com>"],
    "evidence_mode": "all",
    "grading_notes": "Top-level From header of the named email."
  }
}
```

---

## 3. Challenge Families

Allowed `family` values, grouped by the difficulty they primarily belong to:

**Easy families**

| `family` value |
| --- |
| `exact_email_lookup` |
| `message_id_discovery` |
| `header_field_extraction` |
| `attachment_mention` |
| `latest_vs_quoted_sender` |
| `date_normalization` |
| `recipient_role` |
| `body_fact_extraction` |

**Medium families**

| `family` value |
| --- |
| `bounded_work_summary` |
| `search_aggregate` |
| `earliest_latest` |
| `participant_list` |
| `topic_participation` |

**Hard families**

| `family` value |
| --- |
| `thread_reconstruction` |
| `cross_mailbox_corroboration` |
| `timeline_synthesis` |
| `contradiction_resolution` |

Cross-cutting families from the course glossary (`negative_evidence`, `forwarded_copy`, `entity_disambiguation`, `mailbox_hygiene`) may be used when a challenge genuinely fits, but authors should prefer the primary families above.

---

## 4. Golden Answer Object

Nested object at `golden_answer` inside each `golden_set/golden_set.json` record. **Student-visible**: students receive these to run their own evaluation framework.

### Fields

| Field | Type | Description |
| --- | --- | --- |
| `accepted_answer` | object | `{ "value": <canonical answer>, "aliases": [<accepted equivalents>] }`. |
| `evidence_message_ids` | array of string | Accepted Evidence Message-IDs in canonical angle-bracket form `"<...@...>"`. Every id must appear in an in-scope packaged raw email file. |
| `evidence_mode` | string | `"all"` = every listed id required; `"any"` = any one listed id suffices. |
| `grading_notes` | string | How answer equivalence is judged. |

### Rules

- `id`, `difficulty`, and `points` live on the parent Golden Set record.
- Every id in `evidence_message_ids` must appear as the `Message-ID:` header of at least one packaged raw email file.
- For scoped pack challenges, the accepted evidence must resolve inside the scoped pack(s).
- `accepted_answer.value` is the single canonical answer; aliases only add accepted equivalents.

---

## 5. Evidence Representation

Evidence Message-IDs are represented in nested Golden Answers and in the raw email files themselves:

1. **Packaged mail** - each raw email file has a `Message-ID:` header.
2. **Golden Set records** - each nested `golden_answer` lists the subset of Message-IDs accepted as evidence for that challenge.

Message-ID alone is the grading evidence key, but Message-IDs are not guaranteed to be unique across every packaged file. Some Hard packs intentionally include the same source message in more than one pack. Graders and student-built indexes should therefore preserve the packaged path and pack context when they index mail.

### Student-Built Indexes

Students may create their own index if useful. A good local index records at least `message_id`, `subject`, `date`, `from`, `to`, `cc`, `packaged_path`, and `pack`. That index is a tool students build from the raw files, not a shipped dataset artifact.

Every packaged email traces back to the raw maildir through the source fragments in `manifest/sources_<difficulty>.json`; this is the provenance / lineage guarantee referenced in the manifest.

---

## 6. Points and Point Bands

Points are **Fixed Challenge Points**: a single integer per challenge, graded all-or-nothing. Each difficulty has a fixed **Point Band**:

| Difficulty | Point Band (inclusive) |
| --- | --- |
| Easy | 1-3 |
| Medium | 4-7 |
| Hard | 8-10 |

A Golden Set record's `points` must fall inside its difficulty band.

---

## 7. Evidence-Gated Correctness

A student submission scores the challenge's full points only if it provides both:

1. A correct final answer, judged against the Golden Answer per `NORMALIZATION.md`.
2. Accepted Evidence Message-ID(s) satisfying the Golden Answer's `evidence_mode`.

A correct-looking answer without accepted Message-ID evidence scores zero. Grading is all-or-nothing; there is no partial credit.

---

## 8. Manifest Shape

`manifest/manifest.json` records dataset version, the unified student-facing file, the mail layout, per-difficulty counts, and provenance.

### Top-Level Manifest Fields

| Field | Type | Description |
| --- | --- | --- |
| `dataset_name` | string | Human-readable dataset name. |
| `dataset_version` | string | Semantic version tying grades to a corpus version. |
| `created` | string | ISO 8601 creation/update date for this packaged artifact. |
| `target_email_ceiling` | integer | Approximate max packaged emails. |
| `source_corpus` | string | Raw corpus id, `"enron_mail_20150507"`. |
| `mail_layout` | object | `{ "full_mailboxes": "mail/full_mailboxes", "packs": "mail/packs" }`. |
| `files` | object | Path to the unified Golden Set file. |
| `difficulties` | object | Per-difficulty `{ sources_file, email_count }` counts for provenance and point-band reporting. |
| `totals` | object | `{ emails, challenges, easy_challenges, medium_challenges, hard_challenges }`. |
| `provenance_note` | string | Statement that each email traces to raw maildir through the source fragments and packaged paths. |

### Source Manifest Fragments

`manifest/sources_easy.json`, `manifest/sources_medium.json`, and `manifest/sources_hard.json` remain separate source-selection fragments:

```json
{"difficulty": "easy", "sources": ["..."]}
```

Each source record describes one copied unit. `packaged_path` must use the new physical layout:

- Easy `full_mailbox` records: `student_dataset/mail/full_mailboxes/<mailbox>`.
- Medium `bounded_folder` records: `student_dataset/mail/packs/<pack_name>`.
- Hard `curated_pack` records: `student_dataset/mail/packs/<pack_name>`.

Source records keep their existing `difficulty`, `type`, `source_path`, `source_provenance`, `email_count`, `topic`, `scope`, and `parser_pitfalls` fields. They are provenance fragments, not separate student-facing corpora.

---

## Implementation Neutrality

The contract does not require students to use any specific implementation package, framework, or programming language. All deliverables are plain, tool-agnostic formats:

- Golden Set: JSON array.
- Manifests and source fragments: JSON.
- Documentation: Markdown.
- Packaged emails: raw Enron maildir files copied verbatim.

Any language or tooling that can read JSON, Markdown, and plain text files can consume this dataset. The Golden Set intentionally keeps each prompt and official answer together so a student evaluation framework can iterate one record per graded challenge.
