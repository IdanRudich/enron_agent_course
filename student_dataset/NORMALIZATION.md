# Normalization Rules — Beginner Enron Golden Dataset

This document defines how answer values and evidence are **normalized and matched** during
grading. `DATASET_CONTRACT.md` is authoritative for structure/schemas; **this file is
authoritative for value-matching rules**. All challenge authors (tickets 5/6/7) and the
verifier (ticket 8) MUST follow these rules.

Grading is all-or-nothing (Fixed Challenge Points) and evidence-gated: see
`DATASET_CONTRACT.md` §6–§7.

---

## 1. Message-ID (primary evidence key)

Message-ID is the **primary evidence key** for grading.

- **Canonical form:** the value of the email's `Message-ID:` header, in angle-bracket form:
  `<localpart@domain>`. Preserve the angle brackets `<` and `>` as part of the canonical
  form.
- **Trim whitespace:** strip leading/trailing whitespace and any internal line-wrap
  whitespace introduced by header folding before comparing.
- **Preserve inner content exactly:** do not alter case, punctuation, or the `@domain`
  portion inside the brackets. Enron Message-IDs are treated as opaque and matched
  byte-for-byte after trimming.
- **Matching rule:** two Message-IDs match iff, after trimming whitespace, their full
  angle-bracketed strings are identical. A submission that omits the angle brackets but is
  otherwise identical MAY be accepted (add-only tolerance); a submission that changes any
  character inside the brackets does **not** match.
- **Storage:** raw email `Message-ID:` headers and Golden Answers (`evidence_message_ids`)
  use the canonical angle-bracket form.
- **Predicate evidence mode:** when `golden_answer.evidence_mode` is `"predicate"`, a
  submission still must provide at least one Message-ID. Normalize submitted Message-IDs by
  the rules above, resolve them inside the prompt-stated bounds, and pass the evidence gate
  if at least one submitted id satisfies `golden_answer.evidence_predicate`. Extra submitted
  ids that do not satisfy the predicate are ignored for evidence scoring.
- **Curated examples:** in predicate mode, `golden_answer.evidence_message_ids` are curated
  examples/anchors for humans and validators. They are not an exhaustive accepted-evidence
  list.

---

## 2. Date

- **Canonical format: ISO 8601** with explicit UTC offset, e.g.
  `2001-05-14T09:12:00-07:00`. This is the format Golden Answers use as
  `accepted_answer.value` for date questions unless the prompt specifies otherwise.
- **PST/PDT handling:** Enron `Date:` headers are largely US Pacific time. Preserve the
  original UTC offset from the header:
  - PST = UTC−08:00 (`-08:00`)
  - PDT = UTC−07:00 (`-07:00`)
  Convert the raw RFC 2822 header date into ISO 8601 while keeping the same instant and the
  original offset. Do not silently shift to UTC.
- **Equivalent-timezone acceptance (challenge-specific):** for a date/time challenge, a
  student answer that denotes the **same instant** in a different but equivalent
  representation (e.g. the UTC equivalent of a Pacific-offset time) MAY be accepted when the
  challenge's `grading_notes` say so. The default is: accept any representation that
  resolves to the same absolute instant; list explicit accepted forms in `aliases` when a
  challenge wants to constrain this.
- **Date-only questions:** when a prompt asks only for a calendar date, the canonical
  `accepted_answer.value` is `YYYY-MM-DD` in the email's original Pacific offset, and
  `grading_notes` must state the offset used so equivalent-date reasoning is unambiguous.

---

## 3. Address (From / To / Cc / Bcc)

- **Prefer email addresses:** the canonical form of any person/recipient answer is the
  lowercase email address, e.g. `richard.slinger@enron.com`. Email addresses grade
  deterministically and are the default `accepted_answer.value` for sender/recipient
  questions.
- **Accepted alias sets:** display-name variants and known equivalents go in
  `accepted_answer.aliases`, e.g. `["Richard Slinger", "Slinger, Richard", "slinger-r"]`.
  Aliases are accepted **in addition to** the canonical address; they never replace or
  contradict it.
- **Normalization for matching:** trim whitespace; compare email addresses
  case-insensitively; collapse `Last, First` and `First Last` display forms only when both
  are listed as aliases. Do not infer aliases that are not explicitly listed.
- **Multiple recipients:** when an answer is a set of addresses, order does not matter;
  compare as a set of canonicalized addresses.

---

## 4. Aggregate-scope

Aggregate / count challenges (`search_aggregate`, `earliest_latest`, participant/topic
counts) MUST declare exactly what is being counted so scope never expands accidentally. The
scope is declared in the Challenge Question prompt and restated in the Golden Answer
`grading_notes`. A scope is exactly one of:

- **Full mailboxes:** the prompt names the counted mailbox or mailboxes. All folders of those
  mailboxes are in bounds unless the prompt narrows them.
- **Specific folders:** the prompt names the mailbox plus folder bounds.
- **Curated packs:** the prompt names the pack or packs under `mail/packs/`; only those packs
  are in bounds.
- **Union:** an explicit combination of the above; the union members MUST be listed
  explicitly in the prompt and spelled out in `grading_notes`. No implicit inclusion of other
  folders, packs, or mailboxes.

If a date range applies, the prompt-stated date range bounds the count (inclusive) and is
applied after scope selection. Emails outside the declared scope are never counted, even if
they match the topic.

For aggregate challenges that use `evidence_mode: "predicate"`, the predicate is evaluated
after the same prompt-stated scope bounds are applied. For example, a `from_address`
predicate only accepts a matching sender inside the named pack, and a `subject_prefix`
predicate only accepts a matching subject inside the named pack.

---

## 5. Quoted-content (latest-vs-quoted / forwarded-copy)

- **Grade against top-level headers by default.** For sender/recipient/date/subject answers,
  the correct value is taken from the **current email's own top-level headers**
  (`From:`, `To:`, `Cc:`, `Date:`, `Subject:`), NOT from quoted history or forwarded blocks
  in the body.
- **Quoted / forwarded content is only in scope when the prompt explicitly asks about it.**
  A challenge may ask about a sender inside a quoted chain or a forwarded copy; only then is
  the quoted/forwarded value the accepted answer, and `grading_notes` must say so.
- **Latest-vs-quoted sender:** the "latest" / current sender is the top-level `From:`. The
  quoted senders appearing in the body are distractors unless the prompt names them.
- **Forwarded copies / near-duplicates:** when the same content appears in multiple emails,
  the accepted evidence is the specific Message-ID(s) the challenge targets; a different but
  similar copy's Message-ID does not satisfy evidence unless listed in the Golden Answer.

---

## Summary of canonical forms

| Value | Canonical form | Stored in |
| --- | --- | --- |
| Message-ID | `<localpart@domain>` (angle brackets, trimmed) | raw email headers, golden `evidence_message_ids` |
| Date/time | ISO 8601 with original Pacific offset, e.g. `...-07:00` | date answers |
| Date-only | `YYYY-MM-DD` (offset noted in grading_notes) | date-only answers |
| Address | lowercase email address; display names as aliases | golden `accepted_answer` |
