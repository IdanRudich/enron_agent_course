# PRD: Stage 2 Eval Infrastructure and Reference Agent

## Problem Statement

Students have a packaged Enron challenge dataset and a Golden Set, but they do not yet have a standard way to run an agent against the Challenge Questions, build a fresh index, collect Student Agent Submissions, grade evidence-gated answers, or inspect eval results.

Without a shared Agent Interface and Eval Runner, each student would invent a different harness. That makes the course harder to teach, makes submissions hard to compare, and leaves the instructor without a reference implementation that proves the dataset can be solved through valid agent behavior.

The course also needs a reference solution agent that uses the same constraints students are expected to use: a Student Agent CLI, a Minimax Runtime, PydanticAI, a real index over the packaged emails, and no access to Golden Answers during normal operation.

## Solution

Build Stage 2 as three related packages.

The Agent Protocol Package defines the shared EnronAgent interface, common data models, dataset loaders for Public Challenge Records, and a reusable Agent CLI Adapter. Agents expose metadata, index, and prompt commands through an external CLI. The Eval Runner always calls this CLI as a subprocess.

The eval package loads eval-only Golden Answers, creates a Fresh Evaluation Index, calls the Student Agent CLI sequentially, validates JSON results, grades answers and evidence, uses an Answer-Equivalence Judge only as a narrow fallback for answer matching, and writes both machine-readable and human-readable eval results.

The reference solution package implements an EnronAgent using deterministic SQLite/FTS5 indexing and a PydanticAI-powered Solution Agent Prompt Runtime. It uses Minimax through PydanticAI's OpenAI-compatible Chat Completions integration. The solution agent is a separate package from the evaluator and is evaluated through the same external CLI contract as student agents.

Stage 2 should also include student-facing docs, fake-agent tests for the evaluator, mocked judge tests, and a documented manual smoke path for real Minimax integration.

## User Stories

1. As a student, I want a standard agent protocol, so that I can focus on agent behavior instead of inventing an eval harness.
2. As a student, I want my agent to expose an index mode, so that I can prepare a searchable representation of a new dataset before evaluation begins.
3. As a student, I want my agent to expose a prompt mode, so that I can answer one Challenge Question by id.
4. As a student, I want the prompt mode to receive a loaded Public Challenge Record, so that my implementation can work with typed challenge data instead of manually reading raw JSON.
5. As a student, I want the external CLI to receive only the challenge id, so that the CLI contract stays simple and stable.
6. As a student, I want the Public Challenge Record to include difficulty, points, prompt, and expected submission information, so that I know the task and output expectation.
7. As a student, I do not want family or scope routing fields in the Public Challenge Record, so that my agent learns to understand the prompt rather than route from hidden labels.
8. As a student, I want expected submission information to remain visible, so that my agent can produce answers in the expected format.
9. As a student, I want Challenge Question points to remain visible, so that course progression and feedback stay clear.
10. As a student, I want difficulty to remain visible, so that I understand the intended progression from lookup to synthesis.
11. As a student, I want my agent to return JSON on stdout, so that the Eval Runner can parse my result reliably.
12. As a student, I want logs on stderr, so that I can debug my agent without breaking JSON parsing.
13. As a student, I want protocol errors to be reported clearly, so that invalid JSON and invalid submissions are easy to diagnose.
14. As a student, I want prompt crashes and timeouts to be recorded per challenge, so that one broken question does not hide the rest of my results.
15. As a student, I want index failures to abort early, so that I do not waste time running prompts against a broken index.
16. As a student, I want every official eval run to build a fresh index, so that stale local state does not affect results.
17. As a student, I want the evaluator to support running all challenges, so that I can get a complete score.
18. As a student, I want the evaluator to support selected challenge ids, so that I can iterate on a failing case.
19. As a student, I want the evaluator to support selected difficulties, so that I can work through the course in stages.
20. As a student, I want eval results to include total points and max points, so that I can understand my progress.
21. As a student, I want eval results to include per-challenge status, so that I can see which tasks were correct, incorrect, timed out, crashed, or malformed.
22. As a student, I want a concise terminal summary, so that I can quickly see the result of a run.
23. As a student, I want detailed result files, so that I can inspect failures after the run.
24. As a student, I want the Eval Runner to record stderr, so that my debug logs are preserved.
25. As a student, I want raw stdout preserved when parsing fails, so that I can fix broken JSON output.
26. As a student, I want the result directory to include my Agent Name by default, so that multiple agents do not overwrite each other's runs.
27. As a student, I want the result to include the dataset version, so that I know which release was evaluated.
28. As a student, I want the core CLI adapter to handle argument parsing and JSON output, so that I do not repeat fragile boilerplate.
29. As a student, I want submissions to allow extra debug fields, so that I can inspect confidence or tool traces without affecting scoring.
30. As a student, I want the answer field to allow any JSON value, so that list, set, numeric, and object-shaped answers are not forced into strings too early.
31. As a student, I want evidence_message_ids to always be a list, so that the submission shape is predictable.
32. As a student, I want docs that explain metadata, index, and prompt commands, so that I can implement a valid agent quickly.
33. As a student, I want docs to explain Valid Evaluation Behavior, so that I know not to read Golden Answers or hardcode challenge outputs.
34. As a student, I want the course to use Minimax consistently, so that setup and instruction are aligned.
35. As a student, I want agent-scoped Minimax configuration, so that my agent can call the required model provider.
36. As an instructor, I want a local Eval Runner, so that students can self-evaluate during the course.
37. As an instructor, I want all eval runs to use the same Student Agent CLI protocol, so that submissions are comparable.
38. As an instructor, I want agent metadata to include an Agent Name, so that eval outputs can identify the agent being run.
39. As an instructor, I want Agent Name failures to abort before evaluation, so that invalid protocol implementations are caught clearly.
40. As an instructor, I want the Eval Runner to load eval inputs before invoking student code, so that malformed datasets fail fast.
41. As an instructor, I want the Eval Runner to call the agent through an external CLI, so that agents can have separate dependencies and still share one protocol.
42. As an instructor, I want the Eval Runner to sanitize judge credentials from the agent subprocess environment, so that grading credentials are not leaked.
43. As an instructor, I want the Eval Runner to preserve agent-scoped credentials, so that Minimax-based student agents can run.
44. As an instructor, I want deterministic evidence checking, so that unsupported answers score zero.
45. As an instructor, I want fixed all-or-nothing points, so that grading remains simple and explainable.
46. As an instructor, I want an Answer-Equivalence Judge, so that correct paraphrases are not rejected by overly narrow string matching.
47. As an instructor, I want the judge to run only after evidence passes, so that it cannot rescue unsupported answers.
48. As an instructor, I want the judge to see only prompt, expected answer, aliases, expected format, and student answer, so that it does not become an evidence judge.
49. As an instructor, I want judge failures to abort the eval run, so that students are not unfairly marked wrong because the grading service failed.
50. As an instructor, I want judge configuration to fail fast when missing, so that eval behavior is not silently harsher than intended.
51. As an instructor, I want the judge to use structured output, so that equivalent verdicts and rationales can be recorded consistently.
52. As an instructor, I want the judge to use low-temperature settings, so that answer-equivalence grading is as stable as practical.
53. As an instructor, I want the judge to use separate Minimax credentials and model configuration from the solution agent, so that grading and solving can be managed independently.
54. As an instructor, I want predicate-based aggregate evidence, so that aggregate tasks can accept any qualifying supporting message rather than only curated anchor IDs.
55. As an instructor, I want predicate evidence to still require at least one submitted Evidence Message-ID, so that aggregate challenges remain evidence-gated.
56. As an instructor, I want extra non-matching evidence ignored in predicate mode, so that one valid qualifying citation is enough to satisfy evidence.
57. As an instructor, I want Golden Answers to remain eval-only during normal operation, so that the reference solution demonstrates valid behavior.
58. As an instructor, I want the reference solution to avoid reading Golden Answers, so that it proves the tasks can be solved from Public Challenge Records and packaged mail.
59. As an instructor, I want the reference solution to cite emails it retrieved and used, so that it models good evidence behavior for students.
60. As an instructor, I want the reference solution to target 100 percent on the current Golden Set, so that it proves the dataset and tools are sufficient.
61. As an instructor, I do not want 100 percent to block the initial infrastructure merge, so that the harness can be built before the agent is perfected.
62. As a maintainer, I want protocol models in the Agent Protocol Package, so that evaluator and agents share stable shapes.
63. As a maintainer, I want Golden Answer models to live only in the eval package, so that agent packages do not accidentally depend on grading internals.
64. As a maintainer, I want the reusable Agent CLI Adapter in the protocol package, so that every agent uses the same command behavior.
65. As a maintainer, I want the Eval Runner to be tested with fake agents, so that evaluator behavior can be verified without LLM flakiness.
66. As a maintainer, I want judge tests to mock Minimax by default, so that automated tests are deterministic and do not require API keys.
67. As a maintainer, I want an optional real Minimax smoke test, so that provider integration can be verified manually.
68. As a maintainer, I want the solution agent to use deterministic indexing, so that index behavior is reliable, cheap, and debuggable.
69. As a maintainer, I want the solution agent to use PydanticAI only in prompt mode, so that indexing remains deterministic and LLM calls are limited to reasoning.
70. As a maintainer, I want the solution index to use SQLite and FTS5, so that indexed email data is inspectable and supports keyword search without a vector database.
71. As a maintainer, I want the solution tools to expose structured filters, so that exact header, participant, date, and subject operations are deterministic.
72. As a maintainer, I want a Message Aggregation Tool, so that distinct sets, earliest/latest rows, and subject-frequency grouping are not forced into manual LLM counting.
73. As a maintainer, I want count tools to stay simple and exact by default, so that counting does not mix with unrelated result-shaping.
74. As a maintainer, I want aggregate tools to return supporting rows when relevant, so that the agent can cite qualifying evidence naturally.
75. As a maintainer, I want list tools to return sortable metadata-rich rows, so that timeline and synthesis challenges can be solved without loading every body by default.
76. As a maintainer, I want get-message tools to preserve packaged-path provenance, so that duplicate Message-IDs and near-duplicate emails are handled correctly.
77. As a maintainer, I want top-level headers separated from body text, so that latest-vs-quoted and forwarded-copy tasks are less error-prone.
78. As a maintainer, I want date fields parsed into sortable values while preserving original offsets, so that date normalization and extrema tasks are deterministic.
79. As a maintainer, I want participant fields parsed by role, so that From, To, Cc, and Bcc questions can be answered reliably.
80. As a maintainer, I want subject normalization and reply/forward classification, so that aggregate questions can count top-level subject prefixes correctly.
81. As a maintainer, I want docs for the solution-agent tools, so that students can understand the reference without treating it as magic.
82. As a future course author, I want the Stage 2 design to exclude competition and leaderboard concerns, so that future ranking systems can be built separately.
83. As a future course author, I want the Eval Runner to report scores but not rank agents, so that grading and competition remain separate concerns.
84. As a future course author, I want predicate evidence documented at the concept level, so that aggregate evidence remains understandable without exposing grader internals as routing hints.

## Implementation Decisions

- Stage 2 will be built as three packages: an Agent Protocol Package, an eval package, and a separate reference solution agent package.
- The Agent Protocol Package will define shared data structures for Public Challenge Records, expected submission information, Student Agent Submissions, index results, agent metadata, and the EnronAgent protocol.
- The Agent Protocol Package will provide a reusable Agent CLI Adapter that exposes EnronAgent implementations as standard metadata, index, and prompt commands.
- The Eval Runner will invoke agents through the external Student Agent CLI, not by importing agent implementations.
- The Student Agent CLI will print machine-readable JSON only on stdout and diagnostics only on stderr.
- The metadata command will return an Agent Name. Agent version is not part of the protocol.
- The index command will receive a dataset path and index directory, then return an index result with required status and optional stats.
- The prompt command will receive a dataset path, index directory, and challenge id at the CLI boundary.
- The core prompt flow will load the Public Challenge Record and pass that object into EnronAgent.prompt. challenge.id is sufficient; challenge id does not need to be passed separately.
- Public Challenge Records include id, difficulty, points, prompt, and expected submission information.
- Public Challenge Records do not include family, scope, or Golden Answer data.
- expected_submission remains public because it improves output quality and grading alignment.
- difficulty and points remain public because they support course progression and do not leak direct tool routing.
- Student Agent Submissions require challenge_id, answer, and evidence_message_ids.
- Submission answer may be any JSON value.
- evidence_message_ids is always a list of strings.
- Submission objects may include extra fields. The grader ignores extra fields for scoring but preserves them in results.
- A fresh evaluation index is created for each official eval run by default.
- Index failure aborts the eval run.
- Prompt failures are per-challenge failures and evaluation continues.
- Prompt failure statuses include timeout, crash, invalid_json, and invalid_submission.
- Prompt failures score zero.
- The Eval Runner will enforce timeouts for index and prompt subprocesses.
- Challenges run sequentially in Stage 2.
- The Eval Runner supports all challenges, repeated challenge-id selection, and difficulty selection.
- No selector defaults to all challenges. The explicit all flag is equivalent to that default.
- The all flag is mutually exclusive with challenge-id and difficulty selectors.
- Default output paths include a slugified Agent Name and timestamp.
- Explicit output directories are used exactly when provided.
- Eval results include agent_name, dataset_version, timestamps, total_points, max_points, per-challenge results, and durations.
- Machine-readable results are written as JSON.
- Human-readable results are written as Markdown with totals and compact per-challenge rows.
- The terminal prints a concise summary with agent, dataset, score, and result location.
- stderr is saved for every prompt invocation.
- raw stdout is saved when stdout cannot be parsed or validated.
- The Eval Runner fails fast on malformed eval inputs before running agent commands.
- The Eval Runner fails fast when required judge configuration is missing.
- The Eval Runner must not pass judge credentials to the agent subprocess.
- Agent subprocesses may receive agent-scoped Minimax configuration.
- The judge and reference solution use separate Minimax API key, model, and base URL environment variables.
- Students are expected to use Minimax in this course stage, but Minimax configuration is an agent-template and course-doc requirement, not part of the core protocol itself.
- PydanticAI integration with direct Minimax uses the OpenAI-compatible Chat Completions path.
- The initial PydanticAI dependency should use the OpenAI-compatible provider support rather than a native Minimax provider.
- The judge and solution agent both use PydanticAI.
- The judge uses structured output and the grader uses only the equivalent boolean for scoring.
- The judge sees only the challenge prompt, expected answer value, accepted aliases, expected answer format, and student answer.
- The judge does not see email bodies and does not evaluate evidence.
- Evidence is checked before answer matching can use the judge.
- Missing or incorrect evidence cannot be rescued by the judge.
- Judge failures abort the eval run.
- Judge calls should use the lowest practical temperature.
- Evidence modes are all, any, and predicate.
- all mode requires every listed Evidence Message-ID.
- any mode requires at least one listed Evidence Message-ID.
- predicate mode requires at least one submitted Evidence Message-ID satisfying the Evidence Predicate.
- Extra non-matching evidence is ignored for predicate evidence scoring.
- Predicate-Based Aggregate Evidence is used only for aggregate-style challenges where many supporting messages can be valid.
- Curated evidence_message_ids can remain as examples or anchors when evidence_mode is predicate.
- Eval-only Golden Answer data is loaded and used only by the eval package during normal operation.
- The reference solution must not read Golden Answers during normal operation.
- The solution agent is a single general PydanticAI agent with a strong toolset, not hardcoded per-family or per-challenge routing.
- The solution agent indexes deterministically into SQLite with FTS5.
- The solution agent uses PydanticAI only in prompt mode.
- The solution index preserves packaged row identity, Message-ID, packaged path, pack, mailbox, folder, source provenance, top-level headers, parsed addresses, raw and normalized dates, body text, subject normalization, reply/forward classification, and optional attachment metadata.
- get_message supports lookup by Message-ID, packaged row identity, or packaged path where needed, and handles ambiguity by returning matches or requiring disambiguation.
- search_messages supports FTS plus structured filters for Message-ID, sender, recipients, participants, exact subject, subject prefixes, dates, pack, mailbox, folder, and subfolder behavior.
- count_messages returns exact counts over packaged rows by default and supports structured filters.
- aggregate_messages is separate from count_messages and supports distinct values, date min/max, and subject grouping. It returns supporting rows or Message-IDs where relevant.
- list_pack_messages and list_folder_messages return sortable metadata-rich rows with optional body inclusion.
- list_folder_messages has explicit exact-folder versus recursive behavior.
- The reference solution should cite messages it actually retrieved and used.
- The grader checks submitted evidence against Golden Answer evidence rules, not against the agent's private reasoning.
- The Stage 2 completion target is that the reference solution eventually scores 100 percent on the current Golden Set.
- Initial infrastructure merge does not require the reference solution to already score 100 percent.
- Student-facing docs are part of Stage 2.

## Testing Decisions

- The highest test seam for the Agent Protocol Package is the reusable CLI adapter. Tests should invoke metadata, index, and prompt commands as subprocesses and assert stdout, stderr, exit codes, and JSON shapes.
- The highest test seam for the Eval Runner is the external Student Agent CLI. Tests should use fake agents rather than importing internal evaluator functions.
- Fake-agent tests should cover a perfect agent, an incorrect-answer agent, a bad-evidence agent, an invalid-JSON agent, an invalid-submission agent, a crashing agent, and a timing-out agent.
- Eval tests should assert externally observable results: status, points earned, failure kind, preserved stderr, raw stdout on malformed output, total points, max points, and result files.
- Eval tests should verify that index failure aborts the run and prompt failure records a per-challenge failure while continuing.
- Eval tests should verify that a fresh index directory is created for each run.
- Eval tests should verify challenge selection behavior for all, repeated challenge ids, difficulty selection, default all behavior, and mutually exclusive selector failures.
- Eval tests should verify Agent Name handling, including metadata failure and slugified default output directories.
- Eval tests should verify that dataset_version is recorded from the manifest.
- Eval tests should verify that judge credentials are removed from the agent subprocess environment while agent-scoped credentials are preserved.
- Grading tests should cover deterministic answer matching, alias matching, JSON-valued answers, evidence all mode, evidence any mode, and predicate evidence mode.
- Predicate evidence tests should use aggregate-style records and assert that any qualifying Message-ID can pass evidence.
- Predicate evidence tests should assert that empty evidence fails even when the answer is correct.
- Predicate evidence tests should assert that extra non-matching evidence does not fail a challenge when at least one submitted id satisfies the predicate.
- Judge tests should mock Minimax by default.
- Judge tests should cover judge-accepted paraphrases, judge-rejected mismatches, missing judge configuration, and mid-run judge failure.
- Judge tests should assert that the judge is called only when evidence passes and deterministic answer matching fails.
- Judge tests should assert that judge input does not include email bodies or evidence-evaluation data.
- Solution agent tests should focus on deterministic index/tool behavior before LLM behavior.
- Solution index tests should verify parsed top-level headers, role-separated participants, normalized dates, subject normalization, reply/forward classification, packaged-path provenance, and duplicate Message-ID handling.
- Solution tool tests should verify structured search filters, exact counts, aggregate distinct sets, date extrema, subject grouping, and support rows for citation.
- PydanticAI/Minimax integration should have an optional manual smoke test using real credentials.
- Automated tests should not require real Minimax API keys.
- Existing dataset validation remains prior art for artifact-level consistency checks and should continue to pass after Stage 2 data-schema changes.
- Tests should avoid asserting internal implementation details when a subprocess or public tool seam can verify behavior.

## Out of Scope

- Hosted leaderboard service.
- Competition ranking, tie-breakers, or multi-agent tournament behavior.
- Authentication, accounts, or classroom administration.
- A production web UI.
- Adversarial anti-cheat sandboxing.
- Hiding Golden Answers from the released dataset at the filesystem level.
- Supporting non-Minimax student providers in this course stage.
- Native PydanticAI Minimax provider support.
- Relying on Minimax native JSON-schema output before it is smoke-tested.
- Vector search or embeddings for the initial reference solution.
- Parallel challenge execution in Stage 2.
- Partial-credit grading.
- LLM-based evidence judging.
- Importing student agents directly into the evaluator.
- Reusing stale indexes by default.
- Making the reference solution's 100 percent score a hard gate for the first infrastructure merge.

## Further Notes

- The current dataset contains 28 Challenge Questions over 2,892 packaged emails, with 10 Easy, 10 Medium, and 8 Hard challenges.
- Research found the original solution-agent tool names were close, but the signatures need structured filters, aggregation, date ordering, duplicate-aware provenance, and support rows.
- Research found direct Minimax use should go through PydanticAI's OpenAI-compatible Chat Completions integration.
- Research found Medium aggregate evidence needed predicate mode because several aggregate tasks naturally support many valid evidence Message-IDs.
- Predicate evidence has already been added to the aggregate-style Medium challenges and dataset validation passes.
- The issue tracker integration and triage label vocabulary are not available in this workspace, so this PRD is captured locally and should be published to the tracker with the ready-for-agent label when the tracker is available.
