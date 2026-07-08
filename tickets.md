# Tickets: Build The Beginner Enron Golden Dataset

These tickets are artifact-first. The deliverable is the Golden Dataset students receive: selected emails, Challenge Questions, Golden Answers, Evidence Message-IDs, point values, manifests, and documentation.

Supporting scripts are allowed when useful, but they are not the product.

## 1. Define Golden Dataset Artifact Shape

**Type:** AFK

## What to build

Create the empty Golden Dataset structure and its written contract: where selected emails live, where Challenge Questions live, where Golden Answers live, how Evidence Message-IDs are represented, how points are assigned, and how source provenance is recorded.

## Acceptance criteria

- [ ] The Golden Dataset has a clear directory layout for selected mail, curated packs, challenges, Golden Answers, metadata, and documentation.
- [ ] The Challenge Question record shape is documented.
- [ ] The Golden Answer record shape is documented and student-visible.
- [ ] The manifest shape records dataset version, selected sources, counts, and provenance.
- [ ] Normalization rules document Message-ID, date, address, aggregate-scope, and quoted-content conventions.
- [ ] The artifact contract does not require students to use a specific implementation package.

## Blocked by

None - can start immediately.

---

## 2. Select And Copy Easy Source Mailboxes

**Type:** AFK

## What to build

Select the small full mailboxes that will support Easy Challenges, copy them into the Golden Dataset, and record their provenance and approximate counts.

Prefer beginner-friendly sources from the scouting pass such as `slinger-r`, `south-s`, `phanis-s`, `king-j`, `crandell-s`, `dickson-s`, and similarly small mailboxes with clean examples.

## Acceptance criteria

- [ ] Selected Easy source mailboxes are copied into the Golden Dataset with native folder structure preserved.
- [ ] The selected set is small enough for beginner inspection.
- [ ] The manifest lists every included mailbox, source path, and email count.
- [ ] The evidence index includes Message-IDs for included Easy source emails.
- [ ] Known parser pitfalls in these mailboxes are noted for later challenge authoring.

## Blocked by

- Ticket 1: Define Golden Dataset Artifact Shape

---

## 3. Select And Copy Medium Source Slices

**Type:** AFK

## What to build

Select bounded folders and topic slices for Medium Challenges, copy them into the Golden Dataset, and record their source provenance.

Prefer deterministic bounded-search material from the scouting pass such as California/FERC folders, EnronOnline folders, West Positions slices, HourAhead alert slices, CA capacity reports, and compact topic-specific folders.

## Acceptance criteria

- [ ] Medium source slices are copied into the Golden Dataset as curated packs or bounded source folders.
- [ ] Each slice has explicit source provenance and scope metadata.
- [ ] The selected slices support counts, earliest-latest, participant lists, bounded work summaries, and topic participation.
- [ ] The evidence index includes Message-IDs for included Medium source emails.
- [ ] No selected Medium slice requires searching a huge full mailbox.

## Blocked by

- Ticket 1: Define Golden Dataset Artifact Shape

---

## 4. Select And Copy Hard Source Threads

**Type:** AFK

## What to build

Select deterministic multi-message threads and cross-mailbox evidence clusters for Hard Challenges, copy them into the Golden Dataset, and record their source provenance.

Prefer synthesis-friendly material from the scouting pass such as remediation threads, Cage termination threads, cross-mailbox corroboration examples, and outage or regulatory timelines.

## Acceptance criteria

- [ ] Hard source threads are copied into the Golden Dataset as curated packs.
- [ ] Each pack includes enough emails to solve the intended synthesis question without external knowledge.
- [ ] Each pack records original mailbox, folder, source path, and Message-ID provenance.
- [ ] The selected packs support thread reconstruction, cross-mailbox corroboration, timeline synthesis, and contradiction-resolution.
- [ ] The evidence index includes Message-IDs for included Hard source emails.

## Blocked by

- Ticket 1: Define Golden Dataset Artifact Shape

---

## 5. Author Easy Challenge Questions And Golden Answers

**Type:** AFK

## What to build

Author the Easy Challenge Questions and their student-visible Golden Answers against the copied Easy source mailboxes.

The Easy bank should cover exact email lookup, Message-ID discovery, header extraction, attachment mention, latest-vs-quoted sender, date normalization, recipient role, and body fact extraction.

## Acceptance criteria

- [ ] Easy Challenges are worth 1-3 points.
- [ ] Each Easy Challenge is solvable from one known or discoverable email.
- [ ] Each Easy Challenge includes a student-visible Golden Answer.
- [ ] Each Golden Answer includes accepted answer value, accepted Evidence Message-ID, and points.
- [ ] The Easy bank covers every Easy challenge family in `CONTEXT.md`.
- [ ] Challenge prompts are beginner-friendly and explicitly scoped.

## Blocked by

- Ticket 2: Select And Copy Easy Source Mailboxes

---

## 6. Author Medium Challenge Questions And Golden Answers

**Type:** AFK

## What to build

Author the Medium Challenge Questions and their student-visible Golden Answers against the copied Medium source slices.

The Medium bank should cover bounded work summaries, search aggregates, earliest-latest questions, participant lists, and topic participation.

## Acceptance criteria

- [ ] Medium Challenges are worth 4-7 points.
- [ ] Every Medium Challenge has explicit bounds such as mailbox, folder, pack, topic, or date range.
- [ ] Each Medium Challenge has a deterministic Golden Answer.
- [ ] Each Golden Answer includes accepted answer value, accepted Evidence Message-ID evidence, and points.
- [ ] Aggregate questions define exactly which dataset scope is counted.
- [ ] Bounded "what was X working on" questions are scoped tightly enough for deterministic grading.

## Blocked by

- Ticket 3: Select And Copy Medium Source Slices

---

## 7. Author Hard Challenge Questions And Golden Answers

**Type:** AFK

## What to build

Author the Hard Challenge Questions and their student-visible Golden Answers against the copied Hard source threads.

The Hard bank should cover deterministic multi-message synthesis: thread reconstruction, cross-mailbox corroboration, timeline synthesis, and contradiction-resolution.

## Acceptance criteria

- [ ] Hard Challenges are worth 8-10 points.
- [ ] Each Hard Challenge requires evidence from multiple emails or a connected email chain.
- [ ] Each Hard Challenge has a deterministic Golden Answer rather than a broad free-form summary.
- [ ] Each Golden Answer includes accepted answer value, required Evidence Message-IDs, and points.
- [ ] Required Evidence Message-IDs are sufficient to support the expected synthesis.
- [ ] Any ambiguity or unfair noise is documented or the challenge is removed.

## Blocked by

- Ticket 4: Select And Copy Hard Source Threads

---

## 8. Verify Golden Dataset Consistency

**Type:** AFK

## What to build

Verify the completed Golden Dataset artifact for internal consistency.

This may use lightweight one-off scripts or manual checks, but the output is a validation report and fixes to the dataset, not a reusable Python package.

## Acceptance criteria

- [ ] Every Challenge Question has a matching Golden Answer.
- [ ] Every Golden Answer references Evidence Message-IDs present in the packaged dataset.
- [ ] Every Challenge Question has difficulty, points, prompt, and explicit scope where needed.
- [ ] Every point value fits its Point Band.
- [ ] Every source email in curated packs has lineage back to the raw Enron maildir.
- [ ] The validation report lists checked counts, failures found, and fixes made.

## Blocked by

- Ticket 5: Author Easy Challenge Questions And Golden Answers
- Ticket 6: Author Medium Challenge Questions And Golden Answers
- Ticket 7: Author Hard Challenge Questions And Golden Answers

---

## 9. Write Student Usage Documentation

**Type:** AFK

## What to build

Write the student-facing documentation for using the Golden Dataset during the course.

The docs should explain the dataset layout, challenge format, Golden Answer format, Evidence-Gated Correctness, point bands, expected Student Agent Submission format, and how students should use the Golden Answers in their own evaluation framework.

## Acceptance criteria

- [ ] The README explains what is included in the Golden Dataset.
- [ ] The README explains that Golden Answers are intentionally student-visible.
- [ ] The README explains answer + Evidence Message-ID requirements.
- [ ] The README explains point bands and challenge difficulty.
- [ ] The README documents the expected Student Agent Submission shape.
- [ ] The README gives a short example challenge, answer, evidence, and scoring interpretation.

## Blocked by

- Ticket 8: Verify Golden Dataset Consistency
