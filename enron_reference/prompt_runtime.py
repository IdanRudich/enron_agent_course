"""PydanticAI prompt runtime for the reference solution (prompt mode only)."""

from __future__ import annotations

import os
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from enron_challenge.models import PublicChallengeRecord, StudentAgentSubmission

from enron_reference.tools import IndexTools

DEFAULT_MINIMAX_BASE_URL = "https://api.minimax.io/v1"

SYSTEM_PROMPT = """You are the Enron reference solution agent. Use the provided index tools to
retrieve only the messages needed to answer the challenge. Always return a
StudentAgentSubmission with:
- challenge_id set to the given challenge id
- answer set to the requested value in the expected format
- evidence_message_ids listing every Message-ID you actually retrieved and relied on

Prefer structured filters over broad text search. When a Message-ID lookup is
ambiguous across packs or paths, inspect the returned matches and disambiguate
using pack, mailbox, folder, or packaged_path scope from the prompt before citing
evidence. Do not load full bodies unless the question requires body text."""


def agent_env() -> dict[str, str]:
    """Load solution-agent Minimax configuration from environment variables."""
    api_key = os.getenv("ENRON_AGENT_API_KEY") or os.getenv("ENRON_AGENT_MINIMAX_API_KEY")
    model = os.getenv("ENRON_AGENT_MODEL")
    base_url = (
        os.getenv("ENRON_AGENT_BASE_URL")
        or os.getenv("ENRON_AGENT_MINIMAX_BASE_URL")
        or DEFAULT_MINIMAX_BASE_URL
    )
    missing = [name for name, value in [("ENRON_AGENT_API_KEY", api_key), ("ENRON_AGENT_MODEL", model)] if not value]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Missing required environment variable(s): {joined}")
    assert api_key is not None
    assert model is not None
    return {"api_key": api_key, "model": model, "base_url": base_url}


def build_model(model: Model | None = None) -> Model:
    """Create the default Minimax-backed model unless a test override is supplied."""
    if model is not None:
        return model
    config = agent_env()
    return OpenAIChatModel(
        config["model"],
        provider=OpenAIProvider(base_url=config["base_url"], api_key=config["api_key"]),
    )


def create_prompt_agent(tools: IndexTools, *, model: Model | None = None) -> Agent[None, StudentAgentSubmission]:
    """Build a PydanticAI agent wired to deterministic index tools."""
    agent = Agent(
        build_model(model),
        output_type=StudentAgentSubmission,
        system_prompt=SYSTEM_PROMPT,
        retries=2,
    )

    @agent.tool_plain
    def get_message(
        message_id: str | None = None,
        row_id: int | None = None,
        packaged_path: str | None = None,
        scope: dict[str, Any] | None = None,
        include_body: bool = True,
    ) -> dict[str, Any]:
        """Fetch one message by Message-ID, row id, or packaged path."""
        return tools.get_message(
            message_id=message_id,
            row_id=row_id,
            packaged_path=packaged_path,
            scope=scope,
            include_body=include_body,
        )

    @agent.tool_plain
    def search_messages(
        query: str | None = None,
        limit: int = 20,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        order: str = "asc",
    ) -> dict[str, Any]:
        """Search messages with optional FTS query and structured filters."""
        return tools.search_messages(
            query=query,
            limit=limit,
            filters=filters,
            order_by=order_by,
            order=order,
        )

    @agent.tool_plain
    def count_messages(filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """Count packaged rows matching structured filters."""
        return tools.count_messages(filters)

    @agent.tool_plain
    def aggregate_messages(
        filters: dict[str, Any] | None = None,
        distinct: str | None = None,
        metric: str | None = None,
        group_by: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Run distinct, min/max date, or subject grouping aggregations."""
        return tools.aggregate_messages(
            filters,
            distinct=distinct,
            metric=metric,
            group_by=group_by,
            limit=limit,
        )

    @agent.tool_plain
    def list_pack_messages(
        pack_name: str,
        order_by: str = "date",
        order: str = "asc",
        limit: int | None = None,
        offset: int = 0,
        include_body: bool = False,
    ) -> dict[str, Any]:
        """List messages in a curated pack without loading every body by default."""
        return tools.list_pack_messages(
            pack_name,
            order_by=order_by,
            order=order,
            limit=limit,
            offset=offset,
            include_body=include_body,
        )

    @agent.tool_plain
    def list_folder_messages(
        mailbox: str,
        folder: str,
        include_subfolders: bool = False,
        order_by: str = "date",
        order: str = "asc",
        limit: int | None = None,
        offset: int = 0,
        include_body: bool = False,
    ) -> dict[str, Any]:
        """List messages in a mailbox folder with exact or recursive scope."""
        return tools.list_folder_messages(
            mailbox,
            folder,
            include_subfolders=include_subfolders,
            order_by=order_by,
            order=order,
            limit=limit,
            offset=offset,
            include_body=include_body,
        )

    return agent


def run_prompt(
    index_dir: str,
    challenge: PublicChallengeRecord,
    *,
    model: Model | None = None,
) -> StudentAgentSubmission:
    """Execute prompt mode for one public challenge record."""
    tools = IndexTools(index_dir)
    try:
        agent = create_prompt_agent(tools, model=model)
        prompt = (
            f"Challenge id: {challenge.id}\n"
            f"Difficulty: {challenge.difficulty}\n"
            f"Expected answer format: {challenge.expected_submission.answer_format}\n\n"
            f"{challenge.prompt}"
        )
        result = agent.run_sync(prompt)
        submission = result.output
        if submission.challenge_id != challenge.id:
            submission = submission.model_copy(update={"challenge_id": challenge.id})
        return submission
    finally:
        tools.close()
