# Stage 2 Eval Infrastructure Issues

Source PRD: `docs/prd/stage-2-eval-infrastructure-prd.md`

These local issues are ordered by dependency. They use vertical tracer-bullet slices that should each be independently verifiable.

---

## 1. Run a Minimal `EnronAgent` Through the Shared CLI

**Type:** AFK

## What to build

Create the Agent Protocol Package foundation so a minimal `EnronAgent` can be exposed through the shared Student Agent CLI and invoked as an external subprocess. The slice should prove the protocol boundary with metadata, index, and prompt commands, public challenge loading, JSON stdout, stderr diagnostics, and clear protocol errors.

## Acceptance criteria

- [ ] Shared models exist for Public Challenge Records, expected submission information, Student Agent Submissions, index results, agent metadata, and the `EnronAgent` protocol.
- [ ] Public Challenge Records expose `id`, `difficulty`, `points`, `prompt`, and `expected_submission`, and do not expose family, scope, or Golden Answer data.
- [ ] The prompt flow loads a Public Challenge Record from the dataset using only the CLI challenge id before calling `EnronAgent.prompt`.
- [ ] The reusable Agent CLI Adapter exposes `metadata`, `index`, and `prompt` commands.
- [ ] Successful CLI commands print machine-readable JSON only on stdout and diagnostics only on stderr.
- [ ] CLI adapter subprocess tests cover stdout, stderr, exit codes, JSON shapes, invalid JSON, invalid submissions, and clear protocol errors.

## Blocked by

None - can start immediately.

---

## 2. Evaluate a Perfect Fake Agent End-to-End

**Type:** AFK

## What to build

Build the first complete Eval Runner path by running a perfect fake Student Agent CLI against the packaged dataset. The runner should create a fresh evaluation index, call the agent through the external CLI, grade deterministic evidence-gated answers, and write both machine-readable and human-readable results.

## Acceptance criteria

- [ ] The Eval Runner invokes agent metadata, index, and prompt commands through subprocesses rather than importing agent code.
- [ ] Every eval run creates a fresh index directory by default.
- [ ] Challenges run sequentially.
- [ ] A perfect fake agent receives full points for all selected challenges.
- [ ] Eval results include agent name, dataset version, timestamps, durations, total points, max points, and per-challenge results.
- [ ] Results are written as JSON and Markdown.
- [ ] The terminal summary includes agent, dataset, score, and result location.
- [ ] Eval tests verify externally observable behavior through the fake Student Agent CLI.

## Blocked by

- Issue 1: Run a Minimal `EnronAgent` Through the Shared CLI

---

## 3. Keep Eval Runs Useful When Agents Fail

**Type:** AFK

## What to build

Extend the Eval Runner so prompt failures are recorded per challenge while index and metadata failures abort before wasting more work. This slice should make malformed or broken agents easy to diagnose without hiding results for unrelated challenges.

## Acceptance criteria

- [ ] Index failure aborts the eval run before any prompt commands are called.
- [ ] Agent Name metadata failure aborts before evaluation begins.
- [ ] Prompt timeout, crash, invalid JSON, and invalid submission are recorded as per-challenge failures.
- [ ] Prompt failures score zero and evaluation continues to remaining challenges.
- [ ] stderr is preserved for every prompt invocation.
- [ ] Raw stdout is preserved when stdout cannot be parsed or validated.
- [ ] Fake-agent tests cover crashing, timing-out, invalid-JSON, invalid-submission, incorrect-answer, and bad-evidence agents.

## Blocked by

- Issue 2: Evaluate a Perfect Fake Agent End-to-End

---

## 4. Select Challenge Subsets Without Changing the Agent Contract

**Type:** AFK

## What to build

Add challenge selection and result-directory behavior to the Eval Runner while keeping the Student Agent CLI boundary stable. Students should be able to run all challenges, repeated challenge ids, or selected difficulties without exposing extra routing data to the agent.

## Acceptance criteria

- [ ] No selector defaults to all challenges.
- [ ] An explicit all flag is equivalent to the default all behavior.
- [ ] The all flag is mutually exclusive with challenge-id and difficulty selectors.
- [ ] Repeated challenge-id selection is supported.
- [ ] Difficulty selection is supported.
- [ ] Selector failures are reported clearly before agent prompts run.
- [ ] Default output paths include a slugified Agent Name and timestamp.
- [ ] Explicit output directories are used exactly when provided.
- [ ] The recorded result includes the dataset version from the manifest.

## Blocked by

- Issue 2: Evaluate a Perfect Fake Agent End-to-End

---

## 5. Grade Evidence Modes and JSON-Valued Answers

**Type:** AFK

## What to build

Implement the deterministic grader for official eval-only Golden Answers. The grader should support JSON-valued answers, aliases, fixed all-or-nothing points, ignored debug fields, and evidence modes for exact, any, and predicate-based aggregate evidence.

## Acceptance criteria

- [ ] Student submissions require `challenge_id`, `answer`, and `evidence_message_ids`.
- [ ] The `answer` field accepts any JSON value.
- [ ] `evidence_message_ids` must be a list of strings.
- [ ] Extra submission fields are ignored for scoring and preserved in results.
- [ ] Deterministic answer matching handles canonical values and accepted aliases.
- [ ] Evidence `all` mode requires every listed Evidence Message-ID.
- [ ] Evidence `any` mode requires at least one listed Evidence Message-ID.
- [ ] Predicate evidence mode requires at least one submitted Evidence Message-ID satisfying the predicate.
- [ ] Extra non-matching evidence does not fail predicate mode when at least one submitted id satisfies the predicate.
- [ ] Missing or incorrect evidence scores zero even when the answer is correct.

## Blocked by

- Issue 2: Evaluate a Perfect Fake Agent End-to-End

---

## 6. Add the Answer-Equivalence Judge Fallback

**Type:** AFK

## What to build

Add the Answer-Equivalence Judge as a narrow fallback after evidence passes and deterministic answer matching fails. The judge should use separate Minimax/PydanticAI configuration from student or reference agents, receive only answer-equivalence inputs, and abort the eval run on judge failures.

## Acceptance criteria

- [ ] Judge configuration fails fast when required settings are missing.
- [ ] Judge credentials are removed from the agent subprocess environment.
- [ ] Agent-scoped Minimax configuration is preserved for agent subprocesses.
- [ ] The judge and solution agent use separate API key, model, and base URL environment variables.
- [ ] The judge sees only challenge prompt, expected answer value, aliases, expected answer format, and student answer.
- [ ] The judge does not see email bodies or evidence-evaluation data.
- [ ] The judge is called only when evidence passes and deterministic answer matching fails.
- [ ] Judge failures abort the eval run.
- [ ] Mocked judge tests cover accepted paraphrases, rejected mismatches, missing judge configuration, mid-run judge failure, and structured verdict recording.
- [ ] Automated tests do not require real Minimax API keys.

## Blocked by

- Issue 5: Grade Evidence Modes and JSON-Valued Answers

---

## 7. Publish Student-Facing Protocol and Eval Docs

**Type:** AFK

## What to build

Write the Stage 2 student-facing documentation for implementing and evaluating a valid agent. The docs should explain the shared protocol, valid evaluation behavior, result interpretation, Minimax expectations, and the manual smoke path without exposing eval-only Golden Answer internals as agent routing hints.

## Acceptance criteria

- [ ] Docs explain the `metadata`, `index`, and `prompt` commands.
- [ ] Docs explain JSON stdout, stderr diagnostics, and common protocol errors.
- [ ] Docs explain the Public Challenge Record shape and Student Agent Submission shape.
- [ ] Docs explain Valid Evaluation Behavior, including not reading Golden Answers or hardcoding challenge outputs during normal operation.
- [ ] Docs explain fresh indexes, challenge selectors, result files, and terminal summary output.
- [ ] Docs explain that the course stage expects Minimax and agent-scoped Minimax configuration.
- [ ] Docs describe predicate evidence at the concept level without exposing grader-only routing hints.
- [ ] Docs include a documented optional manual smoke path for real Minimax integration.

## Blocked by

- Issue 1: Run a Minimal `EnronAgent` Through the Shared CLI
- Issue 2: Evaluate a Perfect Fake Agent End-to-End
- Issue 3: Keep Eval Runs Useful When Agents Fail
- Issue 4: Select Challenge Subsets Without Changing the Agent Contract
- Issue 5: Grade Evidence Modes and JSON-Valued Answers
- Issue 6: Add the Answer-Equivalence Judge Fallback

---

## 8. Reference Agent Builds an Inspectable SQLite/FTS5 Index

**Type:** AFK

## What to build

Create the reference solution package and prove it can build a deterministic SQLite/FTS5 index over the packaged emails through the same Student Agent CLI protocol. The index should preserve enough structured metadata and provenance for later lookup, search, aggregation, and citation behavior.

## Acceptance criteria

- [ ] The reference solution package depends on the Agent Protocol Package and is separate from the eval package.
- [ ] The reference solution can be invoked through the same external Student Agent CLI contract as student agents.
- [ ] Indexing is deterministic and does not use PydanticAI or Minimax.
- [ ] The SQLite index uses FTS5 for full-text search.
- [ ] Indexed records preserve packaged row identity, Message-ID, packaged path, pack, mailbox, folder, and source provenance.
- [ ] Indexed records separate top-level headers from body text.
- [ ] Date fields are parsed into sortable values while preserving original offsets.
- [ ] Participant fields are parsed by role.
- [ ] Subject normalization and reply/forward classification are stored.
- [ ] Index tests cover duplicate Message-ID handling and packaged-path provenance.

## Blocked by

- Issue 1: Run a Minimal `EnronAgent` Through the Shared CLI

---

## 9. Reference Agent Solves Easy Header and Body Challenges

**Type:** AFK

## What to build

Add the first reference solution prompt behavior for Easy Challenges. The agent should use deterministic index tools plus a PydanticAI prompt runtime only in prompt mode, retrieve the messages it needs, answer simple lookup/header/body tasks, and cite the Evidence Message-IDs it actually used.

## Acceptance criteria

- [ ] The reference solution uses PydanticAI only in prompt mode.
- [ ] Direct Minimax use goes through PydanticAI's OpenAI-compatible Chat Completions integration.
- [ ] `get_message` supports lookup by Message-ID, packaged row identity, or packaged path where needed.
- [ ] `search_messages` supports structured filters needed for Easy Challenge lookup and discovery.
- [ ] Tools expose top-level sender, recipients by role, dates, subjects, body text, and attachment mentions where available.
- [ ] The agent cites retrieved Evidence Message-IDs in Student Agent Submissions.
- [ ] Easy subset eval results are recorded for the reference solution.
- [ ] Tests focus on deterministic tool behavior before LLM behavior.

## Blocked by

- Issue 2: Evaluate a Perfect Fake Agent End-to-End
- Issue 5: Grade Evidence Modes and JSON-Valued Answers
- Issue 8: Reference Agent Builds an Inspectable SQLite/FTS5 Index

---

## 10. Reference Agent Solves Medium Search and Aggregate Challenges

**Type:** AFK

## What to build

Extend the reference solution toolset for Medium Challenges that require bounded search, exact counts, aggregate operations, earliest/latest selection, participant lists, and predicate-compatible supporting rows.

## Acceptance criteria

- [ ] `search_messages` supports structured filters for Message-ID, sender, recipients, participants, exact subject, subject prefixes, dates, pack, mailbox, folder, and subfolder behavior.
- [ ] `count_messages` returns exact counts over packaged rows by default and supports structured filters.
- [ ] `aggregate_messages` is separate from `count_messages`.
- [ ] `aggregate_messages` supports distinct values, date min/max, and subject grouping.
- [ ] Aggregate tools return supporting rows or Message-IDs where relevant.
- [ ] List tools return sortable metadata-rich rows with optional body inclusion.
- [ ] Predicate evidence Medium Challenge examples can be satisfied by qualifying cited messages.
- [ ] Medium subset eval results are recorded for the reference solution.

## Blocked by

- Issue 5: Grade Evidence Modes and JSON-Valued Answers
- Issue 8: Reference Agent Builds an Inspectable SQLite/FTS5 Index
- Issue 9: Reference Agent Solves Easy Header and Body Challenges

---

## 11. Reference Agent Solves Hard Thread and Timeline Challenges

**Type:** AFK

## What to build

Extend the reference solution for Hard Challenges that require multi-message synthesis, thread reconstruction, cross-mailbox corroboration, timeline synthesis, contradiction resolution, and duplicate-aware provenance handling.

## Acceptance criteria

- [ ] `list_pack_messages` returns sortable metadata-rich rows with optional body inclusion.
- [ ] `list_folder_messages` supports explicit exact-folder versus recursive behavior.
- [ ] `get_message` handles ambiguous Message-ID lookup by returning matches or requiring disambiguation.
- [ ] Prompt behavior can retrieve and compare multiple related messages without loading every body by default.
- [ ] The agent cites messages it actually retrieved and used.
- [ ] Hard Challenge behavior covers thread reconstruction, cross-mailbox corroboration, timeline synthesis, and contradiction-resolution cases.
- [ ] Hard subset eval results are recorded for the reference solution.
- [ ] The reference solution target remains eventual 100 percent on the current Golden Set, but this slice does not make 100 percent a hard merge gate.

## Blocked by

- Issue 8: Reference Agent Builds an Inspectable SQLite/FTS5 Index
- Issue 9: Reference Agent Solves Easy Header and Body Challenges
- Issue 10: Reference Agent Solves Medium Search and Aggregate Challenges

---

## 12. Verify Real Minimax Integration and Record Reference Score

**Type:** HITL

## What to build

Run the documented manual smoke path with real Minimax credentials for both the judge and the reference solution, then record the observed integration behavior and reference score. This slice requires human-held credentials and should not make a perfect score a blocker for the initial infrastructure merge.

## Acceptance criteria

- [ ] The manual smoke path documents required judge and solution-agent Minimax environment variables.
- [ ] The smoke path verifies the PydanticAI OpenAI-compatible Chat Completions integration against real Minimax credentials.
- [ ] The smoke path verifies that judge credentials and solution-agent credentials remain separate.
- [ ] The reference solution can be evaluated through the same external CLI contract used for student agents.
- [ ] The current reference score is recorded with dataset version and result location.
- [ ] Any gaps preventing 100 percent are documented as follow-up work.
- [ ] Automated tests continue to pass without real Minimax API keys.

## Blocked by

- Issue 6: Add the Answer-Equivalence Judge Fallback
- Issue 8: Reference Agent Builds an Inspectable SQLite/FTS5 Index
- Issue 9: Reference Agent Solves Easy Header and Body Challenges
- Issue 10: Reference Agent Solves Medium Search and Aggregate Challenges
- Issue 11: Reference Agent Solves Hard Thread and Timeline Challenges
