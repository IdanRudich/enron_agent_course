# Dataset Contract — Beginner Enron Golden Dataset

This document is the **authoritative contract** for the Beginner Enron Golden Dataset
artifact. Every downstream ticket (source selection, challenge authoring, validation,
documentation) MUST follow the directory layout, record shapes, and rules defined here
**verbatim**. When this document and any other note disagree, this document wins for
structure/schemas and `NORMALIZATION.md` wins for value-matching rules.

The artifact is **plain data**: JSON, JSONL, Markdown, and copied raw email files. It is
**not** tied to any implementation package, framework, or language. Students may consume it
with any tooling. See [Implementation neutrality](#implementation-neutrality).

---

## 1. Directory layout

```
student_dataset/
  DATASET_CONTRACT.md        # THIS FILE — the written contract
  NORMALIZATION.md           # value normalization + matching rules
  manifest/
    manifest.json            # top-level manifest skeleton (aggregated by ticket 8)
    sources_easy.json        # Easy source fragment (filled by ticket 2)
    sources_medium.json      # Medium source fragment (filled by ticket 3)
    sources_hard.json        # Hard source fragment (filled by ticket 4)
  mail/
    easy/                    # full mailboxes copied here by ticket 2
    medium/                  # bounded slices / topic packs by ticket 3
    hard/                    # curated thread packs by ticket 4
  evidence/
    evidence_easy.jsonl      # Easy evidence index (ticket 2)
    evidence_medium.jsonl    # Medium evidence index (ticket 3)
    evidence_hard.jsonl      # Hard evidence index (ticket 4)
  challenges/
    challenges_easy.json     # Easy Challenge Questions, JSON array (ticket 5)
    challenges_medium.json   # Medium Challenge Questions, JSON array (ticket 6)
    challenges_hard.json     # Hard Challenge Questions, JSON array (ticket 7)
  golden_answers/
    golden_easy.json         # Easy Golden Answers, JSON array (ticket 5)
    golden_medium.json       # Medium Golden Answers, JSON array (ticket 6)
    golden_hard.json         # Hard Golden Answers, JSON array (ticket 7)
  validation/
    validation_report.md     # written by ticket 8 (validation/.gitkeep until then)
```

### What lives where

| Location | Contents |
| --- | --- |
| `mail/easy/<mailbox>/<folder>/<n>.` | Full beginner-friendly mailboxes, native Enron folder structure preserved. |
| `mail/medium/<pack-or-folder>/...` | Bounded folders and topic slices small enough to search without a huge mailbox. |
| `mail/hard/<pack>/...` | Curated multi-message thread / cross-mailbox synthesis packs. |
| `evidence/evidence_<difficulty>.jsonl` | One record per packaged email mapping Message-ID → canonical metadata + lineage. |
| `challenges/challenges_<difficulty>.json` | Public Challenge Questions (prompt, difficulty, points, family, scope). |
| `golden_answers/golden_<difficulty>.json` | Student-visible Golden Answers (accepted answer, evidence IDs, points, grading notes). |
| `manifest/sources_<difficulty>.json` | Per-difficulty source selection fragment (what was copied, from where, counts). |
| `manifest/manifest.json` | Top-level manifest: version, sources index, counts, provenance. |
| `validation/validation_report.md` | Consistency report produced during verification. |

### Fragment-per-difficulty rule (concurrency safety)

Source-selection tickets (2/3/4) run **in parallel**, and challenge-authoring tickets
(5/6/7) run **in parallel**. To prevent two agents editing the same file:

- There is **no shared multi-difficulty file** that parallel agents both write.
- Each difficulty owns its own `sources_*`, `evidence_*`, `challenges_*`, `golden_*` file
  and its own `mail/<difficulty>/` subtree.
- `manifest/manifest.json` is a **skeleton only** until ticket 8 aggregates it. Tickets
  2/3/4 write their per-difficulty `sources_*.json` fragment and MUST NOT edit
  `manifest.json`.

---

## 2. Challenge Question record

Element of the JSON array in `challenges/challenges_<difficulty>.json`.

### Fields

| Field | Type | Description |
| --- | --- | --- |
| `id` | string | Stable challenge id, `"<difficulty>-NNN"` zero-padded to 3 digits, e.g. `"easy-001"`. Unique across the whole dataset. Never reused. |
| `difficulty` | string | One of `"easy"`, `"medium"`, `"hard"`. Must match the file it lives in. |
| `family` | string | Challenge family; MUST be one of the values in [Challenge families](#3-challenge-families). |
| `points` | integer | Fixed Challenge Points. Must fit the difficulty's Point Band (see [Points](#6-points-and-point-bands)). |
| `prompt` | string | Beginner-friendly task text. MUST state scope explicitly whenever search is required. |
| `scope` | object | Where the answer may be found. See below. |
| `expected_submission` | object | What a valid student submission must contain. See below. |

`scope` object:

| Field | Type | Description |
| --- | --- | --- |
| `mailboxes` | array of string | In-bounds mailbox names (e.g. `["slinger-r"]`), or `[]` if not scoped by mailbox. |
| `folders` | array of string | In-bounds folder names (e.g. `["inbox"]`), or `[]`. |
| `packs` | array of string | In-bounds curated pack names, or `[]`. |
| `date_range` | object or null | `null`, or `{"start": "<ISO 8601>", "end": "<ISO 8601>"}` inclusive. |
| `topic` | string or null | Free-text topic label for topic-bounded challenges, else `null`. |

`expected_submission` object:

| Field | Type | Description |
| --- | --- | --- |
| `answer_format` | string | Short description of the expected answer shape (e.g. `"single email address"`, `"integer count"`, `"ISO 8601 date"`). |
| `requires_evidence_message_ids` | boolean | Whether the student must cite Evidence Message-IDs. Normally `true` (see [Evidence-Gated Correctness](#7-evidence-gated-correctness)). |

### Example

```json
{
  "id": "easy-001",
  "difficulty": "easy",
  "family": "exact_email_lookup",
  "points": 2,
  "prompt": "Open the email with Message-ID <example123@enron.com> in the slinger-r inbox. Who is listed as the sender (From)?",
  "scope": {"mailboxes": ["slinger-r"], "folders": ["inbox"], "packs": [], "date_range": null, "topic": null},
  "expected_submission": {"answer_format": "single email address", "requires_evidence_message_ids": true}
}
```

---

## 3. Challenge families

`family` MUST come from the taxonomy defined in `CONTEXT.md`. The allowed string values,
grouped by the difficulty they belong to:

**Easy families**

| `family` value | CONTEXT.md term |
| --- | --- |
| `exact_email_lookup` | Exact Email Lookup Challenge |
| `message_id_discovery` | Message-ID Discovery Challenge |
| `header_field_extraction` | Header Field Extraction Challenge |
| `attachment_mention` | Attachment Mention Challenge |
| `latest_vs_quoted_sender` | Latest-Vs-Quoted Sender Challenge |
| `date_normalization` | Date Normalization Challenge |
| `recipient_role` | Recipient Role Challenge |
| `body_fact_extraction` | Body Fact Extraction Challenge |

**Medium families**

| `family` value | CONTEXT.md term |
| --- | --- |
| `bounded_work_summary` | Bounded Work Summary Challenge |
| `search_aggregate` | Search Aggregate Challenge |
| `earliest_latest` | Earliest-Latest Challenge |
| `participant_list` | Participant List Challenge |
| `topic_participation` | Topic Participation Challenge |

**Hard families**

| `family` value | CONTEXT.md term |
| --- | --- |
| `thread_reconstruction` | Thread Reconstruction Challenge |
| `cross_mailbox_corroboration` | Cross-Mailbox Corroboration Challenge |
| `timeline_synthesis` | Timeline Synthesis Challenge |
| `contradiction_resolution` | Contradiction-Resolution Challenge |

The `family` value SHOULD match the difficulty group of its file. Cross-cutting families
from `CONTEXT.md` (`negative_evidence`, `forwarded_copy`, `entity_disambiguation`,
`mailbox_hygiene`) MAY be used when a challenge genuinely fits, but authors should prefer
the primary families above and document any cross-cutting use in the prompt.

---

## 4. Golden Answer record

Element of the JSON array in `golden_answers/golden_<difficulty>.json`. **Student-visible**:
students receive these to run their own evaluation framework.

### Fields

| Field | Type | Description |
| --- | --- | --- |
| `id` | string | MUST equal the `id` of the Challenge Question of the same difficulty. |
| `difficulty` | string | Same as the matching Challenge Question. |
| `points` | integer | MUST equal the matching Challenge Question's `points`. |
| `accepted_answer` | object | `{"value": <canonical answer>, "aliases": [<accepted equivalents>]}`. `value` is the canonical form; `aliases` are additional accepted forms (see `NORMALIZATION.md`). |
| `evidence_message_ids` | array of string | Accepted Evidence Message-IDs in canonical angle-bracket form `"<...@...>"`. Every id MUST exist in the packaged dataset / evidence index. |
| `evidence_mode` | string | `"all"` = every listed id required; `"any"` = any one listed id suffices. |
| `grading_notes` | string | How answer equivalence is judged (normalization applied, tolerances, tie-breaks). |

### Rules

- `id` and `points` MUST match the Challenge Question with the same `id`. Ticket 8 verifies
  this.
- Every id in `evidence_message_ids` MUST appear as a `message_id` in the corresponding
  `evidence/evidence_<difficulty>.jsonl` (and thus in the packaged mail).
- `accepted_answer.value` is the single canonical answer; `aliases` never contradict it,
  they only add accepted equivalents.

### Example

```json
{
  "id": "easy-001",
  "difficulty": "easy",
  "points": 2,
  "accepted_answer": {"value": "richard.slinger@enron.com", "aliases": ["Richard Slinger", "slinger-r"]},
  "evidence_message_ids": ["<example123@enron.com>"],
  "evidence_mode": "all",
  "grading_notes": "Address match; accept canonical email or listed display-name aliases per NORMALIZATION.md. Message-ID required."
}
```

---

## 5. Evidence representation

Evidence Message-IDs are represented in **two** places, and they must agree:

1. **Evidence index** — `evidence/evidence_<difficulty>.jsonl`, one JSON object per line,
   one line per packaged email. This is the canonical map from Message-ID → metadata +
   lineage back to the raw maildir.
2. **Inside Golden Answers** — the `evidence_message_ids` array lists the subset of
   Message-IDs that are accepted evidence for that specific challenge.

Every Message-ID referenced by a Golden Answer MUST have a matching record in the evidence
index for the same difficulty.

### Evidence index record fields

| Field | Type | Description |
| --- | --- | --- |
| `message_id` | string | Canonical angle-bracket Message-ID `"<...@...>"`. Primary evidence key. |
| `subject` | string | Email `Subject:` header, trimmed. |
| `date` | string | Canonical date per `NORMALIZATION.md` (ISO 8601). |
| `from` | string | Top-level `From:` (prefer email address). |
| `to` | array of string | Top-level `To:` recipients. |
| `cc` | array of string | Top-level `Cc:` recipients (`[]` if none). |
| `source_mailbox` | string | Original mailbox, e.g. `"slinger-r"`. |
| `source_folder` | string | Original folder, e.g. `"inbox"`. |
| `source_path` | string | Path in the raw corpus, e.g. `"enron_mail_20150507/maildir/slinger-r/inbox/1."`. |
| `packaged_path` | string | Path inside this artifact, e.g. `"student_dataset/mail/easy/slinger-r/inbox/1."`. |
| `pack` | string or null | Curated pack name for medium/hard packs, else `null`. |

### Example (one JSONL line)

```json
{"message_id":"<example123@enron.com>","subject":"Weekly update","date":"2001-05-14T09:12:00-07:00","from":"richard.slinger@enron.com","to":["jeff.dasovich@enron.com"],"cc":[],"source_mailbox":"slinger-r","source_folder":"inbox","source_path":"enron_mail_20150507/maildir/slinger-r/inbox/1.","packaged_path":"student_dataset/mail/easy/slinger-r/inbox/1.","pack":null}
```

Every packaged email traces back to the raw maildir via `source_path`; this is the
provenance / lineage guarantee referenced in the manifest.

---

## 6. Points and Point Bands

Points are **Fixed Challenge Points**: a single integer per challenge, graded
**all-or-nothing** (no partial credit). Each difficulty has a fixed **Point Band**:

| Difficulty | Point Band (inclusive) |
| --- | --- |
| Easy | 1–3 |
| Medium | 4–7 |
| Hard | 8–10 |

A challenge's `points` MUST fall inside its band. The Golden Answer's `points` MUST equal
its Challenge Question's `points`.

---

## 7. Evidence-Gated Correctness

A student submission scores the challenge's full points **only if** it provides both:

1. A correct final answer (judged against the Golden Answer per `NORMALIZATION.md`), **and**
2. Accepted Evidence Message-ID(s) satisfying the Golden Answer's `evidence_mode`
   (`"all"` = every listed id; `"any"` = at least one listed id).

A correct-looking answer **without** accepted Message-ID evidence scores **zero**. Grading
is all-or-nothing: there is no partial credit.

---

## 8. Manifest shape

`manifest/manifest.json` records dataset version, the per-difficulty source fragments,
counts, and provenance. It is a **skeleton** (null counts) until ticket 8 aggregates it.

### Top-level manifest fields

| Field | Type | Description |
| --- | --- | --- |
| `dataset_name` | string | Human-readable dataset name. |
| `dataset_version` | string | Semantic version tying grades to a corpus version. |
| `created` | string or null | ISO 8601 creation timestamp (set at aggregation). |
| `target_email_ceiling` | integer | Approximate max packaged emails (≈6000 for release 1). |
| `source_corpus` | string | Raw corpus id, `"enron_mail_20150507"`. |
| `difficulties` | object | Per-difficulty `{sources_file, email_count}`; counts null until aggregation. |
| `totals` | object | `{emails, challenges, easy_challenges, medium_challenges, hard_challenges}`; null until aggregation. |
| `provenance_note` | string | Statement that each email traces to the raw maildir via the evidence index. |

### Source manifest fragment (`manifest/sources_<difficulty>.json`)

```json
{"difficulty": "easy", "sources": [ <source records> ]}
```

Each **source record** describes one copied unit. `type` selects the variant:

**`full_mailbox`** (Easy — full mailbox copied with native folder structure):

| Field | Type | Description |
| --- | --- | --- |
| `type` | string | `"full_mailbox"`. |
| `mailbox` | string | Mailbox name, e.g. `"slinger-r"`. |
| `source_path` | string | Raw corpus path to the mailbox. |
| `packaged_path` | string | Path inside this artifact. |
| `email_count` | integer | Number of emails copied. |
| `folders` | array of string | Folders included, e.g. `["inbox","sent_items","deleted_items"]`. |
| `parser_pitfalls` | array of string | Known tricky cases noted for challenge authors (`[]` if none). |

**`bounded_folder`** (Medium — a bounded folder / slice copied without the full mailbox):

| Field | Type | Description |
| --- | --- | --- |
| `type` | string | `"bounded_folder"`. |
| `mailbox` | string | Origin mailbox. |
| `source_path` | string | Raw corpus path to the folder / slice. |
| `packaged_path` | string | Path inside this artifact. |
| `email_count` | integer | Number of emails copied. |
| `topic` | string | Topic / theme label for the slice. |
| `scope` | object | Bounds, e.g. `{"folders": [...], "date_range": {...}}`. |
| `parser_pitfalls` | array of string | Known tricky cases (`[]` if none). |

**`curated_pack`** (Medium/Hard — a hand-assembled thread or cross-mailbox cluster):

| Field | Type | Description |
| --- | --- | --- |
| `type` | string | `"curated_pack"`. |
| `pack_name` | string | Unique pack name; matches the pack folder under `mail/<difficulty>/` and `pack` in the evidence index. |
| `packaged_path` | string | Path inside this artifact, e.g. `"student_dataset/mail/hard/<pack_name>"`. |
| `email_count` | integer | Number of emails in the pack. |
| `topic` | string | Topic / theme of the pack. |
| `scope` | object | Bounds description used by challenge authors. |
| `source_provenance` | array of object | Lineage list; each `{"mailbox": ..., "folder": ..., "source_path": ...}` for every origin the pack draws from. |
| `parser_pitfalls` | array of string | Known tricky cases (`[]` if none). |

### Source fragment example

```json
{
  "difficulty": "easy",
  "sources": [
    {"type":"full_mailbox","mailbox":"slinger-r","source_path":"enron_mail_20150507/maildir/slinger-r","packaged_path":"student_dataset/mail/easy/slinger-r","email_count":132,"folders":["inbox","sent_items","deleted_items"],"parser_pitfalls":[]}
  ]
}
```

---

## Implementation neutrality

The contract does **not** require students to use any specific implementation package,
framework, or programming language. All deliverables are plain, tool-agnostic formats:

- Challenge Questions and Golden Answers: **JSON arrays**.
- Evidence index: **JSON Lines (JSONL)**.
- Manifests and source fragments: **JSON**.
- Documentation: **Markdown**.
- Packaged emails: **raw Enron maildir files** copied verbatim.

Any language or tooling that can read JSON/JSONL/Markdown and plain text files can consume
this dataset. Challenge files and Golden Answer files are intentionally **separate** so a
student evaluation framework can load prompts and answers as independent inputs.
