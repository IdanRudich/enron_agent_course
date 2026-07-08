# Beginner Enron Golden Dataset - Student Guide

Welcome to the **Beginner Enron Golden Dataset** (version **0.1.0**). This package gives you a small, real Enron email corpus plus graded challenges so you can practice building AI agents that search email, extract facts, and **cite evidence**.

You do **not** need Python or any specific tooling. Everything is plain files: JSON, Markdown, and raw email text.

---

## What Is Included

| Component | Location | What it is |
| --- | --- | --- |
| **Full mailboxes** | `mail/full_mailboxes/` | Five small full Enron mailboxes, copied with native folder structure. These support Easy lookup and extraction challenges. |
| **Packs** | `mail/packs/` | Medium bounded folders plus Hard curated multi-message packs. Pack names are stated directly in prompts. |
| **Golden Set** | `golden_set/golden_set.json` | 28 graded tasks (10 Easy, 10 Medium, 8 Hard). Each record keeps the challenge prompt, basic metadata, expected submission shape, and nested official answer. |
| **Manifest** | `manifest/manifest.json` | Dataset version, unified file locations, mail layout, counts, and provenance. Source details remain in `manifest/sources_<difficulty>.json`. |
| **Validation report** | `validation/validation_report.md` | Consistency checks run before release. |

**Release totals:** 2,892 emails - 28 challenges - source corpus `enron_mail_20150507`.

The physical mail corpus is no longer split into Easy/Medium/Hard directories. Difficulty is challenge metadata, not a top-level mail partition.

---

## Golden Answers Are Student-Visible

You receive the Golden Answers inside `golden_set/golden_set.json` **on purpose**. This is not a hidden test set.

During the course you submit agent versions every couple of hours. The Golden Answers let you:

- Grade your own submissions locally before you submit.
- See which Message-IDs or predicate rules count as accepted evidence.
- Read `grading_notes` to understand normalization, aliases, and tie-breaks.

Treat each record's `golden_answer` object as the reference implementation for your evaluation framework, not as something to memorize and replay without doing the email work.

The package does **not** include a prebuilt Message-ID index. Building one from the raw mail files is part of the challenge if your agent needs fast lookup.

---

## Evidence-Gated Correctness

Grading uses **Evidence-Gated Correctness**: a submission earns a challenge's full points **only if both** are true:

1. **Correct answer** - your final answer matches the Golden Answer (canonical `accepted_answer.value` or a listed `alias`), per `NORMALIZATION.md`.
2. **Accepted Evidence Message-ID(s)** - you cite Message-ID(s) that satisfy the Golden Answer's `evidence_mode`:
   - `"all"` - every listed id is required.
   - `"any"` - at least one listed id suffices.
   - `"predicate"` - at least one submitted id must satisfy `golden_answer.evidence_predicate`; listed `evidence_message_ids` are curated examples/anchors.

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

When a prompt requires search, the prompt text tells you which mailboxes, folders, packs, date ranges, or topics are in bounds. Stay inside those stated bounds.

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
- **Prompt-stated bounds:** `slinger-r` mailbox, `inbox` folder only
- **Packaged path:** locate the Message-ID by searching or indexing `mail/full_mailboxes/slinger-r/inbox/`.

### Good submission

```json
{
  "challenge_id": "easy-001",
  "answer": "1-800-368-3804",
  "evidence_message_ids": ["<22322411.1075840045955.JavaMail.evans@thyme>"]
}
```

### Golden Answer fields (from `golden_set/golden_set.json`)

```json
{
  "id": "easy-001",
  "points": 2,
  "golden_answer": {
    "accepted_answer": {
      "value": "1-800-368-3804",
      "aliases": ["18003683804", "800-368-3804", "(800) 368-3804"]
    },
    "evidence_message_ids": ["<22322411.1075840045955.JavaMail.evans@thyme>"],
    "evidence_mode": "all"
  }
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
  golden_set/
    golden_set.json          # challenge prompts and nested official answers, sorted easy/medium/hard then id
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

1. Read challenge records from `golden_set/golden_set.json`.
2. Use each challenge's `difficulty`, `points`, and prompt text to choose the in-bounds mail: full mailboxes live under `mail/full_mailboxes/`, and named packs live under `mail/packs/`.
3. Search the raw mail directly, or build your own Message-ID / metadata index from the packaged files.
4. Build your agent to return a **Student Agent Submission** - answer plus evidence Message-IDs.
5. Compare against each record's `golden_answer` object to score yourself before each course submission round.

Good luck - start with Easy challenges to get lookup and citation working, then move to Medium bounded search and Hard multi-email synthesis.
