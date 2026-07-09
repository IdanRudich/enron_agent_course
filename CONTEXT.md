# Context

## Glossary

### Challenge Question
A graded task given to a student agent. Each challenge question has a correct answer, a point value, and one or more accepted evidence Message-IDs. Use this term rather than the informal phrase "eval test".

### Public Challenge Record
The student-facing challenge question data available to an agent. It includes id, difficulty, points, prompt, and expected submission information, but not family, scope, or golden answer data.

### Student Agent Submission
The answer returned by a student's agent for a challenge question. A valid submission includes the final answer and the Message-ID evidence used to support it.

### Submission Answer
The answer value inside a student agent submission. It may be any JSON value, including a string, number, array, or object.

### Student Agent CLI
The external command-line interface implemented by a student agent and called by the eval runner. It exposes separate index and prompt modes.

### Agent Protocol Package
The shared dependency that defines the common agent interface and eval data structures used by the eval runner and agent packages. Student agents and the reference solution depend on it instead of copying protocol models.

### Agent Interface
The shared protocol between the eval runner and an agent package. It defines metadata, index, and prompt commands, their inputs, and their JSON outputs.

### EnronAgent
The protocol-style Python interface implemented by an agent package. It has a name property plus index and prompt methods, and is exposed through the shared agent CLI adapter.

### Agent Name
The human-readable identity reported by an agent implementation through the shared agent protocol and recorded in eval results.

### Agent CLI Adapter
Reusable code in the agent protocol package that exposes an agent implementation as the standard index and prompt command-line interface.

### Agent CLI Result
The JSON object printed to stdout by a successful student agent CLI command. Diagnostic logs belong on stderr, and a non-zero exit means the command failed rather than returning an incorrect answer.

### Agent Index Mode
The student agent CLI mode that prepares a searchable representation of a packaged dataset before evaluation begins.

### Fresh Evaluation Index
An index directory created for a single eval run. The course runner builds a fresh evaluation index by default rather than reusing a previous index; after index mode completes, prompt mode treats the index as read-only.

### Agent Prompt Mode
The student agent CLI mode that receives a challenge question id, loads the corresponding prompt from the packaged dataset, and returns a student agent submission.

### Prompt Challenge Input
The public challenge record loaded from the dataset and passed to an agent implementation during agent prompt mode.

### Solution Agent Index
The reference solution agent's local SQLite index over packaged emails. It stores structured email metadata and uses SQLite FTS5 for full-text search.

### Solution Agent Prompt Runtime
The reference solution agent's PydanticAI-powered runtime used only during agent prompt mode. Indexing remains deterministic.

### Message Aggregation Tool
A solution agent tool for deterministic aggregate operations over indexed messages, such as distinct participant sets, earliest/latest message selection, and subject-frequency grouping.

### Eval Runner
The course tool that calls a student agent CLI, grades the returned submissions, and reports eval results.

### Parallel Challenge Execution
An eval runner behavior where multiple selected challenge questions are prompted concurrently within one eval run.

### Prompt Invocation Failure
A per-challenge student agent CLI failure during agent prompt mode. The eval runner records the failure for that challenge and continues evaluating remaining challenges.

### Prompt Timeout
A prompt invocation failure caused by a student agent CLI command exceeding the per-challenge timeout.

### Prompt Crash
A prompt invocation failure caused by a student agent CLI command exiting non-zero before returning a valid submission.

### Eval Score
The total fixed challenge points earned by a student agent during an eval run.

### Golden Answer
The official student-visible answer for a challenge question. It includes the accepted answer value and accepted evidence Message-IDs; points live on the parent challenge record.

### Eval-Only Golden Answer
A golden answer as loaded and used by the eval package for grading. The reference solution agent does not read golden answers during normal operation.

### Evidence Predicate
A grader-only structured rule inside a golden answer that defines which submitted Message-IDs satisfy predicate-based aggregate evidence. Curated evidence Message-IDs may still be kept as examples or anchors.

### Valid Evaluation Behavior
Student agent behavior that answers challenge questions without reading golden answers or hardcoding known challenge outputs. This is enforced by course rules rather than by a sandbox.

### Evidence Message-ID
An email Message-ID that supports a golden answer or student submission.

### Cited Evidence
Evidence Message-IDs returned in a student agent submission. Cited evidence should identify emails the agent actually retrieved and used to produce the answer.

### Fixed Challenge Points
The 1-10 point value assigned to a challenge question. The value is fixed per question rather than calculated from partial-credit components.

### Point Band
The score range associated with a difficulty level: Easy uses 1-3 points, Medium uses 4-7 points, and Hard uses 8-10 points.

### Evidence-Gated Correctness
A grading rule where a student submission must include accepted Message-ID evidence to receive the challenge question's points.

### Predicate-Based Aggregate Evidence
An aggregate challenge evidence rule where submitted Message-IDs are accepted if their parsed email records satisfy a challenge-specific predicate, rather than only matching a fixed curated list.

### Answer-Equivalence Judge
An LLM-assisted grading fallback used only when accepted evidence is present but deterministic answer matching fails. It can accept semantically equivalent answers, but it cannot override missing or incorrect evidence.

### Judge Input
The narrow data given to the answer-equivalence judge: challenge prompt, expected answer value and aliases, student answer, and expected answer format. It does not include email bodies and does not ask the judge to evaluate evidence.

### Judge Configuration
The API configuration required by the eval runner to use the answer-equivalence judge. If the required judge configuration is missing, evaluation fails before indexing begins.

### Judge Failure
A failure of the answer-equivalence judge during grading. Because the judge is part of the intended grading path, a judge failure aborts the eval run rather than marking a challenge incorrect.

### Minimax Runtime
The LLM provider family used by both the reference solution agent and the answer-equivalence judge. The solution agent and judge use separate API key and model environment variables.

### Student Minimax Runtime
The required LLM provider configuration for student agents in this course stage.

### Easy Challenge
A challenge question whose answer can be verified from one known Message-ID.

### Exact Email Lookup Challenge
An easy challenge where the prompt gives a Message-ID and the student agent must retrieve an atomic fact from that email.

### Message-ID Discovery Challenge
An easy challenge where the prompt gives exact clues about one email and the student agent must return that email's Message-ID.

### Header Field Extraction Challenge
An easy challenge where the student agent must extract a sender, recipient, cc, bcc, subject, or date from one email.

### Attachment Mention Challenge
An easy challenge where the student agent must identify whether an email mentions an attachment or name the attachment mentioned.

### Latest-Vs-Quoted Sender Challenge
An easy challenge where the student agent must distinguish the current email's author from senders in quoted email history.

### Date Normalization Challenge
An easy challenge where the student agent must convert an email date into the requested standard answer format.

### Recipient Role Challenge
An easy challenge where the student agent must distinguish between To, Cc, and Bcc recipients.

### Body Fact Extraction Challenge
An easy challenge where the student agent must extract one explicit fact from the body of a single email.

### Medium Challenge
A challenge question whose answer requires a bounded wide search across emails, usually constrained by a person, topic, date range, or mailbox.

### Bounded Work Summary Challenge
A medium challenge where the student agent must identify what a person worked on within explicit bounds such as dates, mailbox, or topic.

### Search Aggregate Challenge
A medium challenge where the student agent must compute a deterministic count or grouped count from a bounded set of emails.

### Earliest-Latest Challenge
A medium challenge where the student agent must find the earliest or latest email matching explicit criteria.

### Participant List Challenge
A medium challenge where the student agent must return the people involved in a bounded topic, thread, or time window.

### Topic Participation Challenge
A medium challenge where the student agent must determine whether or how a person participated in a bounded topic.

### Hard Challenge
A deterministic challenge question whose answer requires synthesizing evidence from multiple emails, either across a broad set of messages or through a connected email thread.

### Thread Reconstruction Challenge
A hard challenge where the student agent must follow a connected email chain and reconstruct the ordered sequence or final outcome.

### Cross-Mailbox Corroboration Challenge
A hard challenge where the student agent must combine evidence from multiple mailboxes to support one answer.

### Timeline Synthesis Challenge
A hard challenge where the student agent must combine multiple emails into a deterministic sequence of events.

### Contradiction-Resolution Challenge
A hard challenge where the student agent must compare emails that appear to conflict and identify the resolved answer supported by later or stronger evidence.

### Negative Evidence Challenge
A challenge where the student agent must show that no email matching explicit criteria exists within a bounded scope.

### Forwarded-Copy Challenge
A challenge where the student agent must distinguish the current email from quoted, forwarded, or near-duplicate copies of related content.

### Entity Disambiguation Challenge
A challenge where the student agent must distinguish between similarly named people, aliases, email addresses, or organizational identities.

### Mailbox Hygiene Challenge
A challenge where the student agent must handle mailbox structure correctly, including folders, sent mail, deleted items, repeated folder copies, and duplicate-looking messages.
