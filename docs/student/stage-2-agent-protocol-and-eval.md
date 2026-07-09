# Stage 2: Student Agent Protocol and Evaluation

This guide explains how to implement a valid **Enron agent** for Stage 2, expose it through the shared **Student Agent CLI**, and evaluate it with **`enron-eval`**.

The course uses three related packages:

| Package | Role |
| --- | --- |
| `enron_challenge` | Shared protocol models, dataset loaders for **Public Challenge Records**, and the reusable **Agent CLI Adapter** |
| `enron_eval` | Official Eval Runner (`enron-eval`) that invokes your agent as a subprocess, grades submissions, and writes results |
| `enron_reference` | Reference solution (`enron-reference`) that follows the same CLI contract |

Install the project in editable mode from the repo root:

```bash
pip install -e ".[dev]"
```

After installation, `enron-eval` and `enron-reference` are available as console scripts.

---

## 1. The `EnronAgent` Protocol

Your agent implements the `EnronAgent` protocol from `enron_challenge.protocol`:

```python
from enron_challenge.protocol import EnronAgent
from enron_challenge.models import (
    AgentMetadata,
    IndexResult,
    PublicChallengeRecord,
    StudentAgentSubmission,
)
```

Required members:

| Member | Purpose |
| --- | --- |
| `name` (property) | Human-readable **Agent Name** returned by the `metadata` command |
| `index(dataset_path, index_dir)` | Build a searchable index over the packaged dataset |
| `prompt(dataset_path, index_dir, challenge)` | Answer one challenge using the prepared index |

Wire your implementation through the shared CLI adapter:

```python
from enron_challenge.cli import run_cli

def main() -> None:
    run_cli(MyAgent())

if __name__ == "__main__":
    main()
```

The adapter handles argument parsing, JSON output, and protocol error exit codes. You should not reimplement that boilerplate.

---

## 2. Student Agent CLI Commands

The Eval Runner always calls your agent as an **external subprocess**. Your entry point must support three subcommands:

### `metadata`

```bash
python my_agent.py metadata
```

Returns agent identity. **Stdout** must be JSON matching:

```json
{"agent_name": "my-agent-name"}
```

No positional arguments. Agent version is not part of the protocol.

### `index`

```bash
python my_agent.py index <dataset_path> <index_dir>
```

Builds a fresh index for one eval run.

| Argument | Meaning |
| --- | --- |
| `dataset_path` | Path to the packaged dataset directory (for example `student_dataset/`) |
| `index_dir` | Empty directory the Eval Runner created for this run; write your index artifacts here |

**Stdout** must be JSON matching:

```json
{"status": "ok", "stats": {"message_count": 2892}}
```

- `status` is required (typically `"ok"` on success).
- `stats` is optional; include useful diagnostics (counts, paths) if helpful.

Indexing should be **deterministic** where possible. The reference agent builds SQLite/FTS5 without calling an LLM.

### `prompt`

```bash
python my_agent.py prompt <dataset_path> <index_dir> <challenge_id>
```

Answers one challenge.

| Argument | Meaning |
| --- | --- |
| `dataset_path` | Same dataset path passed to `index` |
| `index_dir` | Index directory produced by `index` for this eval run |
| `challenge_id` | Challenge id such as `easy-001` |

At the CLI boundary, only the challenge id is passed. The adapter loads a **Public Challenge Record** from the dataset and passes that typed object to `EnronAgent.prompt`. Your `prompt` implementation receives a `PublicChallengeRecord`, not raw CLI strings.

**Stdout** must be JSON matching a **Student Agent Submission** (see [Section 4](#4-student-agent-submission)).

---

## 3. JSON Stdout, Stderr Diagnostics, and Exit Codes

### Stdout vs stderr

| Stream | Content |
| --- | --- |
| **stdout** | Machine-readable JSON **only** — one JSON object per successful command |
| **stderr** | Human-readable diagnostics: progress logs, debug traces, warnings |

The Eval Runner parses stdout as JSON. Any non-JSON text on stdout breaks evaluation.

Good pattern:

```python
import sys

print(f"indexing {dataset_path} -> {index_dir}", file=sys.stderr)
return IndexResult(status="ok", stats={...})
```

### Protocol exit codes

The Agent CLI Adapter maps protocol failures to explicit exit codes:

| Exit code | Meaning | Typical cause |
| ---: | --- | --- |
| `0` | Success | Valid JSON on stdout |
| `1` | General failure | Crash, unknown challenge id, missing fields in agent logic |
| `2` | `invalid_json` | Agent returned stdout that is not valid JSON |
| `3` | `invalid_submission` | JSON parsed but failed Student Agent Submission validation |

On protocol errors, stderr contains a short message (for example `Invalid submission: ...`). Stdout is empty.

### Eval Runner failure behavior

| Failure | Behavior |
| --- | --- |
| **metadata** failure | Aborts the entire eval run before indexing or prompts |
| **index** failure | Aborts before any `prompt` commands |
| **prompt** failure | Recorded as a per-challenge failure; eval continues with remaining challenges |

Per-challenge prompt failure statuses recorded in results:

| Status | Meaning |
| --- | --- |
| `timeout` | Subprocess exceeded `--timeout` |
| `crash` | Nonzero exit code (other than 2/3) |
| `invalid_json` | Exit code 2, or stdout that cannot be parsed as JSON |
| `invalid_submission` | Exit code 3, or JSON that fails submission validation |
| `incorrect` | Valid submission that did not earn full points |

Prompt failures score **zero** points. stderr is preserved for every prompt. When stdout cannot be parsed or validated, **raw stdout** is preserved in `results.json` for debugging.

---

## 4. Public Challenge Record

During official evaluation, your agent sees a **Public Challenge Record** — the student-facing slice of each challenge. It does **not** include eval-only Golden Answer fields, family labels, or hidden routing metadata.

Shape (from `enron_challenge.models.PublicChallengeRecord`):

```json
{
  "id": "easy-001",
  "difficulty": "easy",
  "points": 2,
  "prompt": "Open the email with Message-ID <...> in the slinger-r mailbox ...",
  "expected_submission": {
    "answer_format": "single phone number",
    "requires_evidence_message_ids": true
  }
}
```

| Field | Purpose |
| --- | --- |
| `id` | Stable challenge id (`easy-001`, `medium-005`, …) |
| `difficulty` | `"easy"`, `"medium"`, or `"hard"` |
| `points` | Fixed all-or-nothing points for this challenge |
| `prompt` | Task text with explicit search bounds (mailbox, folder, pack, dates) |
| `expected_submission.answer_format` | Short description of the answer shape your agent should return |
| `expected_submission.requires_evidence_message_ids` | Whether evidence Message-IDs are required (always `true` in this release) |

Your agent should solve tasks from the **prompt text** and packaged mail, not from hidden labels.

---

## 5. Student Agent Submission

Return this shape from `prompt` (model: `enron_challenge.models.StudentAgentSubmission`):

```json
{
  "challenge_id": "easy-001",
  "answer": "1-800-368-3804",
  "evidence_message_ids": ["<22322411.1075840045955.JavaMail.evans@thyme>"]
}
```

| Field | Rules |
| --- | --- |
| `challenge_id` | Must match the challenge you were asked to solve |
| `answer` | Any JSON value — string, number, list, or object — matching `expected_submission.answer_format` |
| `evidence_message_ids` | List of strings; each string is a Message-ID citing email(s) your agent retrieved and relied on |

**Extra fields** (for example `confidence`, tool traces) are allowed. The grader ignores them for scoring but preserves them in results.

Message-IDs should use angle-bracket form: `<local@domain>`. See `student_dataset/NORMALIZATION.md` for matching rules at grade time.

---

## 6. Valid Evaluation Behavior

Official eval runs enforce **evidence-gated correctness**: you earn a challenge's points only when both the answer and cited evidence pass grading.

### What your agent receives during eval

- The Eval Runner loads challenges internally and passes only **Public Challenge Records** into your `prompt` method.
- Your agent subprocess does **not** receive Golden Answer objects, accepted aliases, evidence modes, or predicate rules through the protocol.

### What you must not do during normal operation

1. **Do not read Golden Answers** inside `metadata`, `index`, or `prompt`. The `golden_set/golden_set.json` file in the dataset includes nested `golden_answer` objects for **local self-grading**, but your agent implementation should solve challenges from prompts and packaged mail.
2. **Do not hardcode** challenge-specific answers or evidence lists keyed by `challenge_id`.
3. **Do not route** on hidden family/scope labels — they are intentionally excluded from Public Challenge Records.

Valid agents **build an index**, **retrieve messages**, **reason over email content**, and **cite Message-IDs they actually used**.

The bundled reference agent (`enron-reference`) follows these rules: deterministic indexing, PydanticAI only in prompt mode, and citations from retrieved rows.

---

## 7. Evidence Modes (Concept Level)

Grading checks that your cited Message-IDs satisfy the challenge's evidence rules. You do not see those rules during eval, but understanding the concepts helps you cite correctly:

| Mode | Concept |
| --- | --- |
| **`all`** | Every required Evidence Message-ID must appear in your submission. Typical for single-email lookup tasks where one specific message proves the answer. |
| **`any`** | At least one of several accepted Message-IDs suffices. Typical when multiple messages could equally support the answer. |
| **`predicate`** | At least one cited Message-ID must qualify as **supporting evidence** for an aggregate-style task (counts, distinct lists, grouped summaries). Many different in-scope messages may qualify — cite messages your tools actually returned while computing the answer. Extra citations that do not qualify are ignored as long as at least one valid citation remains. |

For aggregate and search tasks, design tools that return **supporting rows or Message-IDs alongside counts and aggregates**, so your agent can cite real retrieved mail rather than guessing anchor ids.

A correct answer **without** accepted evidence scores **zero**. There is no partial credit.

---

## 8. Answer-Equivalence Judge (Eval Side)

When evidence passes but deterministic answer matching fails, the Eval Runner may call an **Answer-Equivalence Judge** — a separate LLM that checks semantic equivalence (paraphrases, formatting differences).

Important properties:

- The judge runs **only after evidence passes**; it cannot rescue unsupported citations.
- The judge sees only the challenge prompt, expected answer value, aliases, expected format, and your answer — **not** email bodies.
- Judge configuration is separate from your agent's Minimax credentials (see [Section 11](#11-minimax-configuration)).
- Judge failures **abort** the eval run so you are not marked wrong due to a grading outage.

If you are iterating without judge credentials, use `--skip-judge` (deterministic matching only).

---

## 9. Running Official Evaluation

Use the `enron-eval` command:

```bash
enron-eval \
  --agent-cmd python path/to/my_agent.py \
  --dataset student_dataset \
  --output-dir /tmp/my-eval-run
```

### Required flags

| Flag | Meaning |
| --- | --- |
| `--agent-cmd` | Command prefix for your agent CLI (one or more tokens). Example: `python my_agent.py` or `enron-reference` |
| `--dataset` | Path to the packaged dataset directory |

### Optional flags

| Flag | Meaning |
| --- | --- |
| `--output-dir` | Directory for `results.json` and `results.md`. Default: `<slugified-agent-name>_<UTC-timestamp>` in the current working directory |
| `--timeout` | Subprocess timeout in seconds for metadata, index, and each prompt |
| `--skip-judge` | Skip the answer-equivalence judge (useful for local testing without judge API keys) |

### Fresh evaluation index

Every official eval run:

1. Calls `metadata` to read your Agent Name.
2. Creates a **new temporary index directory**.
3. Calls `index` into that directory.
4. Calls `prompt` sequentially for each selected challenge using the same index directory.

Stale local indexes from previous runs are never reused. If `index` fails, no prompts run.

### Challenge selectors

Selectors choose which challenges to run. They are mutually exclusive.

| Selector | Behavior |
| --- | --- |
| *(none)* | Run **all** challenges (default) |
| `--all` | Same as default — run all challenges |
| `--challenge-id ID` | Run one id; **repeat** the flag for multiple ids or duplicates |
| `--difficulty LEVEL` | Run all challenges with that difficulty; repeat for multiple levels |

Examples:

```bash
# All challenges (default)
enron-eval --agent-cmd python my_agent.py --dataset student_dataset

# Single failing challenge
enron-eval --agent-cmd python my_agent.py --dataset student_dataset \
  --challenge-id medium-003

# Easy subset only
enron-eval --agent-cmd python my_agent.py --dataset student_dataset \
  --difficulty easy

# Invalid id fails before any prompts
enron-eval --agent-cmd python my_agent.py --dataset student_dataset \
  --challenge-id does-not-exist
```

Selector errors (unknown id, no matches for difficulty) abort before agent prompts.

---

## 10. Result Files and Terminal Summary

Each eval run writes two files under the output directory:

### `results.json`

Machine-readable run record (`EvalRunResult`):

| Field | Meaning |
| --- | --- |
| `agent_name` | From your `metadata` command |
| `dataset_version` | From `manifest/manifest.json` |
| `started_at`, `finished_at`, `duration_seconds` | Run timestamps and wall time |
| `total_points`, `max_points` | Aggregate score |
| `index_dir` | Temporary index path used for this run (removed after the run completes) |
| `challenges[]` | Per-challenge results |

Each challenge entry includes:

| Field | Meaning |
| --- | --- |
| `challenge_id`, `difficulty`, `max_points`, `points_earned` | Identity and score |
| `status` | `correct`, `incorrect`, or a failure kind |
| `duration_seconds` | Time for that prompt subprocess |
| `submission` | Parsed submission when prompt succeeded |
| `grading` | `answer_match`, `evidence_pass`, `evidence_mode`, optional judge fields |
| `stderr` | Agent stderr from that prompt |
| `failure_kind`, `raw_stdout` | Present on prompt failures |

### `results.md`

Human-readable summary: agent, dataset version, timestamps, total score, and a compact per-challenge table.

### Terminal summary

On success, `enron-eval` prints a per-challenge table with score, grading columns, and output paths:

```
Eval complete
  Agent:    my-agent-name
  Dataset:  0.1.0
  Duration: 45.2s
  Score:    120/142 (85%)

  Challenge       Diff   Score  Status       Answer  Evidence  Judge   Time
  ------------------------------------------------------------------------------
  easy-001        easy   1/1    correct      yes     yes       —       4.2s
  ...

  JSON: /path/to/output/results.json
  MD:   /path/to/output/results.md
```

Use `--verbose` for per-challenge progress on stderr during the run.

For the full Minimax smoke path (loads `.env`, validates credentials, runs reference agent checks), use:

```bash
enron-smoke          # single easy-001 challenge (default)
enron-smoke easy     # all easy challenges
enron-smoke full     # all 28 challenges
```

Fatal runner errors (metadata/index/selector/judge config) print to stderr and exit `1`.

---

## 11. Minimax Configuration

Stage 2 expects agents that call **Minimax** through **PydanticAI's OpenAI-compatible Chat Completions** integration (`OpenAIChatModel` + `OpenAIProvider`). Direct Minimax HTTP calls outside PydanticAI are not the course pattern.

Minimax settings are **agent-scoped** — they are not part of the core CLI protocol, but your prompt runtime needs them when using an LLM.

### Agent subprocess variables

Set these for your agent (prompt mode):

| Variable | Required | Purpose |
| --- | --- | --- |
| `ENRON_AGENT_API_KEY` | Yes | Minimax API key for your agent |
| `ENRON_AGENT_MODEL` | Yes | Model name (for example `MiniMax-M3`) |
| `ENRON_AGENT_BASE_URL` | No | Defaults to `https://api.minimax.io/v1` |

The reference agent also accepts legacy aliases `ENRON_AGENT_MINIMAX_API_KEY` and `ENRON_AGENT_MINIMAX_BASE_URL` for the key and base URL.

### Judge variables (Eval Runner host)

The Eval Runner reads judge credentials from **its own environment**, not from your agent:

| Variable | Required | Purpose |
| --- | --- | --- |
| `ENRON_JUDGE_API_KEY` | Yes* | Minimax API key for the answer-equivalence judge |
| `ENRON_JUDGE_MODEL` | Yes* | Judge model name |
| `ENRON_JUDGE_BASE_URL` | No | Defaults to `https://api.minimax.io/v1` |

\*Not required when using `--skip-judge`.

### Credential isolation

Before spawning your agent, the Eval Runner **removes judge environment variables** from the agent subprocess. Your agent keeps `ENRON_AGENT_*` variables. This prevents grading credentials from leaking into student code while still allowing your agent to call Minimax.

Use **separate API keys** for agent and judge in production smoke tests.

### Reference integration pattern

```python
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

model = OpenAIChatModel(
    os.environ["ENRON_AGENT_MODEL"],
    provider=OpenAIProvider(
        base_url=os.getenv("ENRON_AGENT_BASE_URL", "https://api.minimax.io/v1"),
        api_key=os.environ["ENRON_AGENT_API_KEY"],
    ),
)
agent = Agent(model, output_type=StudentAgentSubmission, ...)
```

See `docs/research/pydanticai_minimax_enron_integration.md` for deeper integration notes.

---

## 12. Optional Manual Smoke Path (Real Minimax)

Use this path to verify real Minimax connectivity for both the reference agent and the judge. Automated tests mock the judge and do not require API keys.

### Quick path: `enron-smoke`

Copy `.env.example` to `.env`, fill in credentials, then run:

```bash
enron-smoke          # one easy challenge (easy-001)
enron-smoke easy     # all 10 easy challenges
enron-smoke full     # all 28 challenges
```

`enron-smoke` loads `.env` from the current directory, validates agent and judge credentials, runs reference-agent metadata/index/prompt checks, then invokes `enron-eval` with verbose progress.

### Manual step-by-step (same contract)

If you prefer to run each step yourself:

```bash
export ENRON_AGENT_API_KEY="your-agent-key"
export ENRON_AGENT_MODEL="MiniMax-M3"
export ENRON_AGENT_BASE_URL="https://api.minimax.io/v1"

export ENRON_JUDGE_API_KEY="your-judge-key"
export ENRON_JUDGE_MODEL="MiniMax-M3"
export ENRON_JUDGE_BASE_URL="https://api.minimax.io/v1"
```

Use distinct keys for agent and judge when possible.

### 2. Smoke-test agent CLI commands

```bash
# Metadata
enron-reference metadata

# Index (writes to a temp dir you choose)
mkdir -p /tmp/enron-smoke-index
enron-reference index student_dataset /tmp/enron-smoke-index

# Single prompt (requires agent env vars)
enron-reference prompt student_dataset /tmp/enron-smoke-index easy-001
```

Confirm JSON on stdout and diagnostics on stderr.

### 3. Run a small official eval

Start with one Easy challenge before a full run:

```bash
enron-eval \
  --agent-cmd enron-reference \
  --dataset student_dataset \
  --challenge-id easy-001 \
  --output-dir /tmp/enron-smoke-eval
```

Inspect `/tmp/enron-smoke-eval/results.json` for `grading.answer_match`, `grading.evidence_pass`, and any `judge_used` fields.

### 4. Run a broader eval

```bash
enron-eval \
  --agent-cmd enron-reference \
  --dataset student_dataset \
  --difficulty easy \
  --output-dir /tmp/enron-smoke-easy
```

Record the dataset version, score, and result path from the terminal summary.

### 5. Verify credential separation

When running through `enron-eval`, judge variables are stripped from the agent subprocess. A quick check: your agent should read `ENRON_AGENT_*` successfully while `ENRON_JUDGE_*` is absent in agent code that logs sanitized environment keys during development.

---

## 13. Local Self-Grading vs Official Eval

| Activity | Golden Answers | Index | Purpose |
| --- | --- | --- | --- |
| **Local self-grading** | You may read `golden_set/golden_set.json` | Your own persistent index is fine | Iterate quickly, understand normalization |
| **Official `enron-eval`** | Loaded only inside the eval package; not passed to your agent | Fresh temp index every run | Fair, comparable scoring |

Use local Golden Answers to **validate your grader and normalization**, not to **short-circuit agent reasoning**. Your submitted agent should demonstrate retrieval and citation from packaged mail.

For answer-matching and Message-ID normalization details, see `student_dataset/NORMALIZATION.md`. For full dataset schemas, see `student_dataset/DATASET_CONTRACT.md`.

---

## Quick Reference

### Implement

1. Implement `EnronAgent` (`name`, `index`, `prompt`).
2. Call `run_cli()` from `enron_challenge.cli`.
3. Print JSON on stdout; logs on stderr.
4. Return `StudentAgentSubmission` with `challenge_id`, `answer`, and `evidence_message_ids`.
5. Configure `ENRON_AGENT_*` for LLM prompt mode.

### Evaluate

```bash
enron-eval --agent-cmd python my_agent.py --dataset student_dataset
```

### Debug failures

| Symptom | Check |
| --- | --- |
| `invalid_json` | Ensure stdout is exactly one JSON object; move prints to stderr |
| `invalid_submission` | Validate against `StudentAgentSubmission`; `evidence_message_ids` must be a list of strings |
| `Agent metadata failed` | `metadata` must return `{"agent_name": "..."}` with nonempty name |
| `Agent index failed` | Fix indexing errors before debugging prompts |
| Zero points with `evidence_pass: false` | Cite Message-IDs you retrieved; for aggregates, include supporting citations from tool results |
| Eval aborts mid-run | Judge misconfiguration or judge API failure — check `ENRON_JUDGE_*` or use `--skip-judge` |
