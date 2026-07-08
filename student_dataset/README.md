# Beginner Enron Golden Dataset - Student Guide

Welcome to the **Beginner Enron Golden Dataset** (version **0.1.0**). This package gives you a small, real Enron email corpus plus graded challenges so you can practice building AI agents that search email, extract facts, and **cite evidence**.

You do **not** need Python or any specific tooling. Everything is plain files: JSON, JSONL, Markdown, and raw email text.

---

## What Is Included

| Component | Location | What it is |
| --- | --- | --- |
| **Full mailboxes** | `mail/full_mailboxes/` | Five small full Enron mailboxes, copied with native folder structure. These support Easy lookup and extraction challenges. |
| **Packs** | `mail/packs/` | Medium bounded folders plus Hard curated multi-message packs. Pack names match `scope.packs` and evidence `pack` values. |
| **Challenge Questions** | `challenges/challenges.json` | 28 graded tasks (10 Easy, 10 Medium, 8 Hard). Each record keeps `difficulty`, point value, challenge family, and explicit search scope. |
| **Golden Answers** | `golden_answers/golden_answers.json` | Official answers for every challenge: accepted values, required Evidence Message-IDs, evidence mode, and grading notes. |
| **Evidence index** | `evidence/evidence.jsonl` | One record per packaged email, mapping Message-ID to metadata, source lineage, packaged path, pack, and original `difficulty`. |
| **Manifest** | `manifest/manifest.json` | Dataset version, unified file locations, mail layout, counts, and provenance. Source details remain in `manifest/sources_<difficulty>.json`. |
| **Validation report** | `validation/validation_report.md` | Consistency checks run before release. |

**Release totals:** 2,892 emails - 28 challenges - source corpus `enron_mail_20150507`.

The physical mail corpus is no longer split into Easy/Medium/Hard directories. Difficulty is challenge metadata, not a top-level mail partition.

---

## Golden Answers Are Student-Visible

You receive the Golden Answers **on purpose**. This is not a hidden test set.

During the course you submit agent versions every couple of hours. The Golden Answers let you:

- Grade your own submissions locally before you submit.
- See exactly which Message-IDs count as accepted evidence.
- Read `grading_notes` to understand normalization, aliases, and tie-breaks.

Treat Golden Answers as the reference implementation for your evaluation framework, not as something to memorize and replay without doing the email work.

---

## Evidence-Gated Correctness

Grading uses **Evidence-Gated Correctness**: a submission earns a challenge's full points **only if both** are true:

1. **Correct answer** - your final answer matches the Golden Answer (canonical `accepted_answer.value` or a listed `alias`), per `NORMALIZATION.md`.
2. **Accepted Evidence Message-ID(s)** - you cite Message-ID(s) that satisfy the Golden Answer's `evidence_mode`:
   - `"all"` - every listed id is required.
   - `"any"` - at least one listed id suffices.

A correct-looking answer **without** accepted Message-ID evidence scores **zero**. There is no partial credit.

Every challenge in this release sets `requires_evidence_message_ids: true`. Always return the Message-ID(s) your agent relied on.

**Message-ID format:** canonical form is angle-bracketed, e.g. `<22322411.1075840045955.JavaMail.evans@thyme>`. See `NORMALIZATION.md` for trimming and matching rules.

---

## Point Bands and Challenge Difficulty

Each challenge has **Fixed Challenge Points** (one integer, all-or-nothing). Difficulty sets the **Point Band**:

| Difficulty | Points | Emails represented | Challenges | Where to search |
| --- | --- | ---: | ---: | --- |
| **Easy** | 1-3 | 1,329 | 10 | `mail/full_mailboxes/<mailbox>/...` |
| **Medium** | 4-7 | 1,500 | 10 | `mail/packs/<pack_name>/...` |
| **Hard** | 8-10 | 63 | 8 | `mail/packs/<pack_name>/...` |

Challenge families remain grouped by difficulty:

**Easy** - `exact_email_lookup`, `message_id_discovery`, `header_field_extraction`, `attachment_mention`, `latest_vs_quoted_sender`, `date_normalization`, `recipient_role`, `body_fact_extraction`

**Medium** - `bounded_work_summary`, `search_aggregate`, `earliest_latest`, `participant_list`, `topic_participation`

**Hard** - `thread_reconstruction`, `cross_mailbox_corroboration`, `timeline_synthesis`, `contradiction_resolution`

When a prompt requires search, its `scope` object tells you which mailboxes, folders, packs, date ranges, or topics are in bounds. Stay inside that scope.

---

## Student Agent Submission

A **Student Agent Submission** is what your agent returns for one challenge. A valid submission has two parts:

| Field | Description |
| --- | --- |
| `answer` | Your final answer, in the shape described by the challenge's `expected_submission.answer_format` (e.g. a single email address, an integer count, an ISO 8601 date). |
| `evidence_message_ids` | An array of Evidence Message-ID strings in angle-bracket form, citing the email(s) that support your answer. |

**Example submission object** (illustrative shape - use whatever structure your agent framework prefers, as long as it carries these two concepts):

```json
{
  "challenge_id": "easy-001",
  "answer": "1-800-368-3804",
  "evidence_message_ids": ["<22322411.1075840045955.JavaMail.evans@thyme>"]
}
```

Your course tooling may wrap this differently, but graders expect both the answer and the evidence Message-IDs together.

---

## Worked Example: `easy-001`

### Challenge prompt

> Open the email with Message-ID `<22322411.1075840045955.JavaMail.evans@thyme>` in the slinger-r mailbox (inbox folder). The body gives a contact phone number for AON. What is that AON contact phone number?

- **Points:** 2 (Easy band 1-3)
- **Family:** `exact_email_lookup`
- **Scope:** `slinger-r` mailbox, `inbox` folder only
- **Packaged path:** use `evidence/evidence.jsonl` to resolve the Message-ID to `mail/full_mailboxes/slinger-r/inbox/17.`

### Good submission

```json
{
  "challenge_id": "easy-001",
  "answer": "1-800-368-3804",
  "evidence_message_ids": ["<22322411.1075840045955.JavaMail.evans@thyme>"]
}
```

### Golden Answer fields (from `golden_answers/golden_answers.json`)

```json
{
  "id": "easy-001",
  "points": 2,
  "accepted_answer": {
    "value": "1-800-368-3804",
    "aliases": ["18003683804", "800-368-3804", "(800) 368-3804"]
  },
  "evidence_message_ids": ["<22322411.1075840045955.JavaMail.evans@thyme>"],
  "evidence_mode": "all"
}
```

The right answer alone is not enough; cite the accepted Message-ID evidence.

---

## Directory Layout

```
student_dataset/
  README.md
  DATASET_CONTRACT.md        # full schemas and field definitions (authoritative)
  NORMALIZATION.md           # how answers and Message-IDs are matched at grade time
  mail/
    full_mailboxes/          # full small mailboxes
    packs/                   # medium bounded folders and hard curated packs
  evidence/
    evidence.jsonl           # unified Message-ID index, one email per line
  challenges/
    challenges.json          # unified challenge array, sorted easy/medium/hard then id
  golden_answers/
    golden_answers.json      # unified golden-answer array, sorted the same way
  manifest/
    manifest.json
    sources_easy.json
    sources_medium.json
    sources_hard.json
  validation/
    validate_dataset.py
    validation_report.md
```

For complete record shapes, see **`DATASET_CONTRACT.md`**. For answer-matching rules, see **`NORMALIZATION.md`**.

---

## Quick Start

1. Read challenges from `challenges/challenges.json`.
2. Use each challenge's `difficulty`, `points`, and `scope` to choose the in-bounds mail: full mailboxes live under `mail/full_mailboxes/`, and named packs live under `mail/packs/`.
3. Use `evidence/evidence.jsonl` to resolve Message-IDs to `packaged_path` values and to inspect metadata.
4. Build your agent to return a **Student Agent Submission** - answer plus evidence Message-IDs.
5. Compare against `golden_answers/golden_answers.json` to score yourself before each course submission round.

Good luck - start with Easy challenges to get lookup and citation working, then move to Medium bounded search and Hard multi-email synthesis.
