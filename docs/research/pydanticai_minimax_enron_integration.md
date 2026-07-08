# PydanticAI + MINIMAX Integration for the Enron Solution Agent and Judge

Date: 2026-07-09

## Question

What is the correct current way to use MINIMAX with PydanticAI for the planned Enron solution agent and answer-equivalence judge?

The design needs separate solution-agent and judge credentials/models:

- `ENRON_AGENT_MINIMAX_API_KEY`
- `ENRON_AGENT_MODEL`
- `ENRON_JUDGE_MINIMAX_API_KEY`
- `ENRON_JUDGE_MODEL`

## Short Answer

Use PydanticAI's OpenAI-compatible Chat Completions path: `OpenAIChatModel` plus `OpenAIProvider(base_url="https://api.minimax.io/v1", api_key=...)`. Do not use `OpenAIResponsesModel` for direct MINIMAX unless MINIMAX later documents OpenAI Responses API compatibility; MINIMAX's first-party OpenAI-compatible docs are for `/v1/chat/completions`.

PydanticAI does not currently have a direct native MINIMAX provider. There is an open upstream PydanticAI issue for native MiniMax support, and current PydanticAI source contains a MiniMax profile only for AWS Bedrock, not for direct MINIMAX API keys. MINIMAX does, however, officially expose an OpenAI-compatible API usable through PydanticAI's OpenAI-compatible model/provider support.

## Primary Sources Used

- PydanticAI model overview, provider/profile definitions, OpenAI-compatible providers, and concurrency limiting: <https://ai.pydantic.dev/models/overview/>
- PydanticAI OpenAI model docs, install instructions, `OpenAIChatModel`, `OpenAIProvider`, and OpenAI-compatible provider examples: <https://ai.pydantic.dev/models/openai/> and <https://ai.pydantic.dev/api/models/openai/>
- PydanticAI structured output docs for `output_type`, default tool-output mode, `ToolOutput`, `NativeOutput`, and `PromptedOutput`: <https://ai.pydantic.dev/output/>
- PydanticAI MiniMax native-provider request, still open: <https://github.com/pydantic/pydantic-ai/issues/5966>
- PydanticAI Bedrock provider source showing `bedrock_minimax_model_profile`, i.e. MiniMax only via Bedrock profile in that path: <https://github.com/pydantic/pydantic-ai/blob/950aed93/pydantic_ai_slim/pydantic_ai/providers/bedrock.py>
- MINIMAX OpenAI SDK docs: <https://platform.minimax.io/docs/api-reference/text-openai-api>
- MINIMAX model invocation docs and URL configuration: <https://platform.minimax.io/docs/guides/text-generation>
- MINIMAX OpenAI-compatible Chat Completions API reference: <https://platform.minimax.io/docs/api-reference/text-chat-openai>
- MINIMAX M3 tool use and interleaved thinking guide: <https://platform.minimax.io/docs/guides/text-m3-function-call>
- MINIMAX rate limits and error codes: <https://platform.minimax.io/docs/guides/rate-limits>, <https://platform.minimax.io/docs/api-reference/errorcode>

## Native Provider Status

PydanticAI's current model overview lists built-in support for OpenAI, Anthropic, Gemini, xAI, Bedrock, Cerebras, Cohere, Groq, Hugging Face, Mistral, OpenRouter, and Z.AI. It separately says OpenAI-compatible providers can be used with `OpenAIChatModel`.

The upstream PydanticAI issue "Native minimax support" is open as of 2026-06-17 and describes native MiniMax support as a new-provider request, with the bot summary explicitly contrasting "first-class settings/profiles" against "hand-built OpenAI-client overrides." That means direct MINIMAX support should currently be treated as not native.

There is MiniMax-related PydanticAI source for Bedrock: `bedrock_minimax_model_profile(model_name)` and a `provider_to_profile` entry for `'minimax'`. That is useful only when invoking MiniMax through AWS Bedrock's Converse API, not when using a MINIMAX subscription key against `api.minimax.io`.

## Recommended PydanticAI Integration Path

Use the OpenAI-compatible Chat Completions model:

```python
import os

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

MINIMAX_BASE_URL = "https://api.minimax.io/v1"

agent_model = OpenAIChatModel(
    os.environ["ENRON_AGENT_MODEL"],
    provider=OpenAIProvider(
        base_url=os.getenv("ENRON_AGENT_MINIMAX_BASE_URL", MINIMAX_BASE_URL),
        api_key=os.environ["ENRON_AGENT_MINIMAX_API_KEY"],
    ),
)

judge_model = OpenAIChatModel(
    os.environ["ENRON_JUDGE_MODEL"],
    provider=OpenAIProvider(
        base_url=os.getenv("ENRON_JUDGE_MINIMAX_BASE_URL", MINIMAX_BASE_URL),
        api_key=os.environ["ENRON_JUDGE_MINIMAX_API_KEY"],
    ),
)

solution_agent = Agent(agent_model)
judge = Agent(judge_model)
```

Why this shape:

- PydanticAI documents `pydantic-ai-slim[openai]` or full `pydantic-ai` for OpenAI/OpenAI-compatible APIs.
- PydanticAI documents `OpenAIChatModel` as the class backing OpenAI-compatible providers.
- PydanticAI documents `OpenAIProvider(base_url=..., api_key=...)` for non-OpenAI compatible endpoints.
- MINIMAX documents `OPENAI_BASE_URL=https://api.minimax.io/v1`, `OPENAI_API_KEY=${YOUR_API_KEY}`, and `client.chat.completions.create(model="MiniMax-M3", ...)` against `/v1/chat/completions`.

Avoid relying on global `OPENAI_API_KEY` and `OPENAI_BASE_URL` for this project because the solution agent and judge need separate credentials and model names. Load the Enron-specific variables and pass them into `OpenAIProvider` directly.

## Dependencies and Import Paths

Required Python dependency:

```bash
pydantic-ai-slim[openai]
```

The full `pydantic-ai` package is also acceptable. No MINIMAX-specific Python SDK is required for the PydanticAI path because MINIMAX's direct integration is through the OpenAI-compatible API and the OpenAI Python SDK dependency used by PydanticAI's OpenAI provider.

Relevant imports:

```python
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
```

For structured judge outputs, likely imports:

```python
from pydantic import BaseModel
from pydantic_ai import Agent, PromptedOutput, ToolOutput
```

Use `NativeOutput` only after confirming the exact MINIMAX model and endpoint support native JSON-schema response format through the OpenAI-compatible Chat Completions endpoint.

## Environment Variables

Recommended project-specific variables:

```bash
export ENRON_AGENT_MINIMAX_API_KEY="..."
export ENRON_AGENT_MODEL="MiniMax-M3"
export ENRON_AGENT_MINIMAX_BASE_URL="https://api.minimax.io/v1"

export ENRON_JUDGE_MINIMAX_API_KEY="..."
export ENRON_JUDGE_MODEL="MiniMax-M3"
export ENRON_JUDGE_MINIMAX_BASE_URL="https://api.minimax.io/v1"
```

The two base URL variables can default to `https://api.minimax.io/v1` in code. Keeping them separate is useful if the judge and solution agent are ever routed differently, or if a regional endpoint is needed. MINIMAX's M3 tool-use guide also documents `https://api.minimaxi.com/v1` for users in China.

If configuration simplicity is preferred, a single shared `ENRON_MINIMAX_BASE_URL` with the same default is also reasonable. The important part is not to use global `OPENAI_*` variables for both roles unless both roles intentionally share one key and endpoint.

## Model Choice

Recommended default for both roles: `MiniMax-M3`.

MINIMAX describes `MiniMax-M3` as the latest M-series language model for agentic reasoning, tool use, coding, long context, and multimodal tasks, with a 1,000,000-token context window. The answer-equivalence judge may not need the full agentic capability, but using the same family initially reduces integration variability. After the evaluation harness is stable, cost/latency can be tested against lower-cost or high-speed M2.x models.

MINIMAX's OpenAI SDK docs list these OpenAI-compatible model names:

- `MiniMax-M3`
- `MiniMax-M2.7`
- `MiniMax-M2.7-highspeed`
- `MiniMax-M2.5`
- `MiniMax-M2.5-highspeed`
- `MiniMax-M2.1`
- `MiniMax-M2.1-highspeed`
- `MiniMax-M2`

## Caveats for the Solution Agent

### Tool Calling

MINIMAX's OpenAI-compatible Chat Completions API supports `tools` with function definitions. The API reference shows `finish_reason: "tool_calls"` and returns `message.tool_calls`, and the guide says to echo the full assistant message back with the matching `role: tool` message.

This is compatible in shape with PydanticAI's default tool-output and function-tool approach. The main caveat is MiniMax-M3's thinking/interleaved-thinking behavior: MINIMAX says the complete model response must be preserved in history, including `tool_calls` and thinking fields. PydanticAI manages normal message history, but we should run a small tool-call smoke test before committing to long Enron runs, especially if enabling `reasoning_split`.

### Thinking Fields

For `MiniMax-M3`, thinking is on by default unless `thinking: {"type": "disabled"}` is passed. MINIMAX says `reasoning_split=True` separates thinking into `reasoning_content` and `reasoning_details`, but those fields must be preserved in later turns for best interleaved-thinking performance.

PydanticAI does not have a MiniMax-specific profile that knows about these MiniMax-only fields. For the Enron solution agent, start without `reasoning_split` unless we verify PydanticAI/OpenAI SDK pass-through and message-history round-tripping. If thinking text leaking into `content` interferes with answer extraction or judging, pass MiniMax-specific extra request fields through model settings only after a smoke test.

### Structured Output and JSON Mode

PydanticAI supports structured outputs through `output_type`. By default, it uses the model's tool-calling capability to return structured data. It also supports `NativeOutput` for model-native JSON-schema response formats and `PromptedOutput` for schema-in-instructions output.

For direct MINIMAX OpenAI-compatible Chat Completions, the official Chat Completions API reference does not document `response_format`. The separate MINIMAX `/v1/text/chatcompletion_v2` reference documents `response_format` as only supported by `MiniMax-Text-01`, not by the listed M-series OpenAI-compatible Chat Completions models.

Implication:

- For the tool-using solution agent, use normal PydanticAI tools and avoid native structured output unless tested.
- For the answer-equivalence judge, prefer `ToolOutput` or plain prompted JSON plus Pydantic validation/retry.
- Do not assume `NativeOutput` or OpenAI strict structured outputs work for `MiniMax-M3` through `https://api.minimax.io/v1/chat/completions`.

If PydanticAI sends strict tool definitions that MINIMAX rejects, configure a custom `OpenAIModelProfile`, for example setting `openai_supports_strict_tool_definition=False`. PydanticAI documents custom profiles for OpenAI-compatible providers whose schema/tool restrictions differ from OpenAI.

### Streaming

MINIMAX's OpenAI-compatible endpoint supports `stream: true` and `stream_options.include_usage`. PydanticAI's OpenAI chat model supports streamed responses, but streaming with tool calls and MiniMax thinking fields should be smoke-tested. For the judge, non-streaming is simpler and preferred.

### Rate Limits and Retries

MINIMAX documents LLM rate limits in RPM and TPM. As of the rate-limit page used for this note:

- `MiniMax-M3`: 200 RPM, 10,000,000 TPM
- `MiniMax-M2.7-highspeed`, `MiniMax-M2.5-highspeed`, `MiniMax-M2.1-highspeed`, `MiniMax-M2`: 500 RPM, 20,000,000 TPM

MINIMAX error code `1002` is rate limit, `1001` is request timeout, `1039` is token limit, `2045` is rate growth limit, and `2056` is usage limit exceeded. Use PydanticAI's `ConcurrencyLimitedModel` or an application-level limiter for batch evaluation runs, especially when running solution-agent calls and judge calls concurrently.

## Recommended Initial Configuration

Solution agent:

- `ENRON_AGENT_MODEL=MiniMax-M3`
- Use `OpenAIChatModel` with `OpenAIProvider`.
- Use PydanticAI tools normally.
- Start non-streaming for initial correctness tests.
- Add concurrency limiting before large batch runs.

Judge:

- `ENRON_JUDGE_MODEL=MiniMax-M3` initially.
- Use `OpenAIChatModel` with a separate `OpenAIProvider` and judge API key.
- Keep the judge non-streaming.
- Use a small structured schema with Pydantic validation, but do not depend on native JSON-schema response format until tested.
- Consider disabling thinking for judge calls if pass-through is verified and judge answers are otherwise polluted by `<think>` content.

## Open Questions to Validate With a Smoke Test

1. Does `MiniMax-M3` through PydanticAI's `OpenAIChatModel` round-trip tool calls cleanly across multiple tool steps without losing MiniMax thinking fields?
2. Does PydanticAI's default structured `output_type` via output tools work reliably with `MiniMax-M3`, including retries after validation failures?
3. Does MINIMAX reject any PydanticAI-generated strict tool schema fields, requiring `OpenAIModelProfile(openai_supports_strict_tool_definition=False)` or a schema transformer?
4. Can MiniMax-specific request fields such as `thinking`, `reasoning_split`, and `service_tier` be passed cleanly through PydanticAI model settings or a custom OpenAI client path?

## Final Recommendation

Proceed with direct MINIMAX via the OpenAI-compatible Chat Completions integration:

```text
PydanticAI Agent
  -> OpenAIChatModel
  -> OpenAIProvider(base_url="https://api.minimax.io/v1", api_key=<role-specific key>)
  -> MINIMAX /v1/chat/completions
```

This is the lowest-risk current path for both the Enron solution agent and judge. Treat native PydanticAI MINIMAX support as future work, and treat native JSON-schema output as unconfirmed for `MiniMax-M3` on the OpenAI-compatible endpoint.
