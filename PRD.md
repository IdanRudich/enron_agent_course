# PRD: Beginner Enron Agent Challenge Dataset

## Problem Statement

Students in a single-day AI agent training need a beginner-friendly dataset and challenge set for learning how to build agents that search, inspect, reason over, and cite evidence from real email data.

The raw Enron corpus is too large and noisy for this setting: it contains roughly 517,000 emails across 150 mailboxes, with many large mailboxes exceeding 20,000 emails. Giving students the full corpus, or even 20 high-value full mailboxes, would make the course less beginner-friendly and would push students toward brute-force token spend instead of deliberate tool use.

The course needs a smaller student dataset, a golden challenge set, deterministic scoring, and evidence-gated grading. Students submit an agent version every couple of hours in a Codewars-style loop, and each submission should be rated against known answers, accepted Evidence Message-IDs, and Fixed Challenge Points.

## Solution

Build a hybrid Enron student dataset and challenge package.

The student dataset should combine:

- A small set of full, beginner-friendly mailboxes that preserve real mailbox structure for Easy and Medium tool-building practice.
- Curated topic and thread packs extracted from larger high-density mailboxes for Medium and Hard challenges.
- Metadata that explains dataset contents, mailbox provenance, challenge scope, and normalization rules.
- A public challenge catalog containing prompts, difficulty, and point values.
- Student-visible Golden Answers containing accepted answers, accepted Evidence Message-IDs, and scoring data for the students' own evaluation framework.

The recommended target is roughly 6,000 emails or less for the first release, rather than 20 full topical mailboxes. A smaller golden challenge slice can be selected from that dataset for the actual graded tasks.

The course should use the settled challenge taxonomy:

- Easy Challenges are worth 1-3 points and are solvable from one known or discoverable email.
- Medium Challenges are worth 4-7 points and require bounded wide search with deterministic answers.
- Hard Challenges are worth 8-10 points and require deterministic multi-message synthesis.
- Every Student Agent Submission must include the final answer and Evidence Message-ID evidence.
- Evidence-Gated Correctness means a correct-looking answer without accepted Message-ID evidence does not receive points.

## User Stories

1. As a course instructor, I want students to receive a small Enron dataset, so that they can focus on agent behavior instead of corpus scale.
2. As a course instructor, I want the dataset to preserve real mailbox folders, so that students learn mailbox hygiene.
3. As a course instructor, I want curated topic packs from large mailboxes, so that students can solve rich questions without searching 20,000-email mailboxes.
4. As a course instructor, I want each Challenge Question to have a difficulty level, so that students can progress from lookup to synthesis.
5. As a course instructor, I want each Challenge Question to have Fixed Challenge Points, so that scoring is clear before students submit.
6. As a course instructor, I want each Golden Answer to include accepted Evidence Message-IDs, so that grading can verify evidence rather than trust unsupported answers.
7. As a course instructor, I want students to receive the Golden Answers, so that they can run their own evaluation framework while improving their agents.
8. As a course instructor, I want challenge and Golden Answer files to be separated, so that students can run prompts and evaluations as distinct steps.
9. As a course instructor, I want deterministic challenges, so that submissions can be graded automatically.
10. As a course instructor, I want to avoid broad free-form summary grading, so that the course does not depend on subjective judge behavior.
11. As a course instructor, I want Easy Challenges to include exact Message-ID lookup, so that students learn how to retrieve a specific email quickly.
12. As a course instructor, I want Easy Challenges to include Message-ID discovery, so that students learn to search from exact clues.
13. As a course instructor, I want Easy Challenges to include header extraction, so that students learn the difference between From, To, Cc, Bcc, Subject, and Date.
14. As a course instructor, I want Easy Challenges to include attachment mention detection, so that students learn the difference between text mentions and actual attachments.
15. As a course instructor, I want Easy Challenges to include latest-vs-quoted sender tasks, so that students do not confuse top-level headers with quoted history.
16. As a course instructor, I want Easy Challenges to include date normalization, so that students learn to handle PST, PDT, and messy email date formats.
17. As a course instructor, I want Easy Challenges to include recipient-role tasks, so that students distinguish To, Cc, and Bcc.
18. As a course instructor, I want Easy Challenges to include body fact extraction, so that students learn direct evidence retrieval before synthesis.
19. As a course instructor, I want Medium Challenges to include bounded work summaries, so that students can answer "what was X working on" only within explicit scope.
20. As a course instructor, I want Medium Challenges to include search aggregates, so that agents can be tested on counts and grouped counts.
21. As a course instructor, I want Medium Challenges to include earliest-latest tasks, so that agents learn scoped ordering and date handling.
22. As a course instructor, I want Medium Challenges to include participant lists, so that agents can extract people from bounded topics or threads.
23. As a course instructor, I want Medium Challenges to include topic participation, so that agents can determine whether and how a person participated in a bounded topic.
24. As a course instructor, I want Hard Challenges to include thread reconstruction, so that students build agents that follow email chains.
25. As a course instructor, I want Hard Challenges to include cross-mailbox corroboration, so that students build agents that combine evidence from multiple sources.
26. As a course instructor, I want Hard Challenges to include timeline synthesis, so that students build agents that combine emails into a deterministic sequence of events.
27. As a course instructor, I want Hard Challenges to include contradiction-resolution, so that students build agents that compare conflicting evidence and identify the supported answer.
28. As a student, I want the dataset to be small enough to inspect with tools, so that I can iterate quickly during a one-day course.
29. As a student, I want challenge prompts to specify scope, so that I know which mailboxes, folders, dates, or topics are in bounds.
30. As a student, I want point values to be visible, so that I can decide which challenges to prioritize.
31. As a student, I want evidence expectations to be explicit, so that I know my answer must cite Message-IDs.
32. As a student, I want beginner challenges that reward exact lookup, so that I can get early feedback from simple agent tools.
33. As a student, I want medium challenges that require bounded search, so that I can improve retrieval without being overwhelmed.
34. As a student, I want hard challenges that require multi-email reasoning, so that I can test whether my agent can synthesize evidence.
35. As a grader, I want submissions to use a consistent answer format, so that results can be parsed automatically.
36. As a grader, I want Message-ID normalization, so that evidence matching is robust to minor formatting differences.
37. As a grader, I want date normalization rules, so that equivalent date answers can be compared fairly.
38. As a grader, I want address alias handling, so that display names and email addresses can be accepted when intentionally equivalent.
39. As a grader, I want clear aggregate scopes, so that counts do not accidentally include packs or unrelated folders.
40. As a maintainer, I want challenge and Golden Answer files to be separated, so that the student evaluation framework can consume them independently.
41. As a maintainer, I want pack lineage metadata, so that each curated email can be traced back to its original mailbox and folder.
42. As a maintainer, I want challenge IDs to be stable, so that student results can be compared across submission rounds.
43. As a maintainer, I want dataset version metadata, so that grades can be tied to the exact corpus version.
44. As a maintainer, I want known parser pitfalls documented, so that course staff can explain tricky cases.
45. As a future course author, I want the challenge taxonomy recorded in the project glossary, so that new challenges use the same vocabulary.

## Implementation Decisions

- The first release should use a hybrid dataset strategy rather than the full Enron corpus, 20 full topical mailboxes, or a tiny answer-only pack.
- The first release target should be approximately 6,000 emails or less, with a smaller subset of those emails directly tied to the graded Golden Answers.
- Full small mailboxes should be used for Easy and some Medium practice because they preserve natural folder structure and mailbox hygiene.
- Curated topic packs should be used for high-value Medium and Hard material from large mailboxes that would otherwise overwhelm beginners.
- Candidate full small mailboxes should come from scout-identified beginner-friendly sources such as `slinger-r`, `south-s`, `phanis-s`, `king-j`, `crandell-s`, `dickson-s`, and selected similar small mailboxes.
- Candidate Medium bounded folders and slices should include sources such as California/FERC folders, EnronOnline folders, West Positions slices, HourAhead alert slices, and compact topic-specific folders.
- Candidate Hard curated packs should include deterministic thread and synthesis clusters such as remediation threads, Cage termination threads, cross-mailbox corroboration examples, and selected outage or regulatory timelines.
- Challenge prompts must always define scope explicitly when search is required.
- Bounded "what was X working on" questions are Medium when constrained by dates, mailbox, folder, or topic.
- Unbounded work-history questions are Hard or out of scope for the first release because they are difficult to grade deterministically.
- The public challenge catalog should include challenge ID, difficulty, point value, prompt, and expected submission format; search bounds belong in the natural-language prompt.
- The student-visible Golden Answer store should include challenge ID, accepted answer values, accepted Evidence Message-IDs, accepted aliases where needed, point value, and grading notes.
- The evidence index should map Message-IDs to canonical metadata such as subject, date, participants, source mailbox, source folder, and pack provenance.
- The dataset manifest should record dataset version, selected full mailboxes, selected curated packs, approximate email counts, and challenge coverage.
- Pack lineage should preserve the original mailbox and folder provenance for each curated email.
- Message-ID should be the primary evidence key for grading.
- Message-ID matching should trim whitespace and accept angle-bracket-preserving canonical forms.
- Date answers should use one documented canonical format, with challenge-specific acceptance for equivalent timezone-normalized answers.
- Address answers should prefer email addresses for deterministic grading and may include accepted alias sets for known display-name variants.
- Latest-vs-quoted and forwarded-copy questions should grade against top-level headers unless the prompt explicitly asks about quoted or forwarded content.
- Aggregate questions must specify whether the scope includes full mailboxes, specific folders, curated packs, or a union of those sources.
- Attachment challenges should distinguish text mentions, Outlook-style attachment markers, and actual MIME attachments.
- The grader should support all-or-nothing Fixed Challenge Points for the first release.
- Partial-credit grading is out of scope for the first release.
- LLM judge grading is out of scope for the first release.
- The primary deliverable is the Golden Dataset itself: selected emails, Challenge Questions, Golden Answers, Evidence Message-IDs, Fixed Challenge Points, manifests, and student documentation.
- Any scripts or checks created during implementation are supporting utilities for assembling and verifying the Golden Dataset, not the product students are meant to build against.
- The highest-value validation boundary is package consistency: every challenge references emails and Message-IDs that exist in the packaged dataset.
- A second high-value validation boundary is package completeness: the released student package must include the dataset, challenges, Golden Answers, and evaluation inputs together.

## Testing Decisions

- Validation should focus on externally observable dataset facts: packaged email contents, challenge validity, Golden Answer evidence, normalization rules, and package completeness.
- Validation should not require students to use a particular implementation language or package.
- The challenge catalog validator should confirm that every Challenge Question has a stable ID, difficulty, Fixed Challenge Points, prompt, and explicit scope when needed.
- The Golden Answer validator should confirm that every accepted Evidence Message-ID exists in the packaged dataset or evidence index.
- The student package validator should confirm that challenge files and Golden Answer files are both present and can be consumed as separate inputs by the students' evaluation framework.
- Evidence-Gated Correctness should be documented directly: a correct answer without accepted Message-ID evidence should score zero.
- Message-ID normalization should be documented for whitespace, casing around domains where applicable, and angle-bracket handling.
- Date normalization should be documented for PST/PDT conversion and challenge-specific date formats.
- Address normalization should be documented for exact email addresses and accepted aliases.
- Search aggregate challenges should be manually or mechanically verified with folder-scoped and pack-scoped counts to prevent accidental scope expansion.
- Latest-vs-quoted sender challenges should be verified against messages that contain quoted `From` lines and forwarded headers.
- Attachment mention challenges should distinguish body text mentions, Outlook-style markers, and MIME attachment metadata.
- Thread reconstruction and timeline synthesis challenges should be verified against the exact packaged emails students receive.
- Negative Evidence Challenges should only be included when the bounded search scope can be verified.
- There is no existing test prior art in this repo yet, so lightweight validation scripts are acceptable if they help verify the dataset artifact.

## Out of Scope

- Shipping the full Enron corpus to students.
- Shipping 20 large topical mailboxes as the default beginner dataset.
- Building an answer-only toy dataset that removes real mailbox structure.
- Depending on unavailable attachment bodies for Golden Answers.
- Free-form essay grading for the first release.
- LLM judge scoring for the first release.
- Partial-credit scoring for the first release.
- Unbounded "what was X working on" questions for the first release.
- Questions that require external historical knowledge beyond the packaged emails.
- A production web UI for challenge browsing or grading.
- A hosted leaderboard service.
- Authentication, accounts, or multi-classroom administration.
- Automatic generation of all challenges without human validation.
- Guaranteeing that every scout-suggested challenge will appear in the final challenge catalog.

## Further Notes

- The project glossary in `CONTEXT.md` is the source of truth for challenge vocabulary.
- The initial scout work found that a pure full-mailbox strategy is either too large or topically weak.
- The initial scout work found that a pure curated-pack strategy is token efficient but weaker for teaching real mailbox hygiene.
- The hybrid strategy best supports a one-day beginner course while preserving realistic search and synthesis behavior.
- The current workspace does not expose a configured project issue tracker, so this PRD is written locally and should be published to the tracker when one is configured.
- The next planning step is to split this PRD into implementation issues for dataset selection, package generation, challenge authoring, golden answer validation, grading, and course documentation.
