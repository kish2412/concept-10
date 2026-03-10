from __future__ import annotations

from typing import Any, TypedDict

from langchain_core.messages import BaseMessage


class OrchestrationState(TypedDict):
    request_id: str
    session_id: str
    agent_id: str
    messages: list[BaseMessage]
    context: dict[str, Any]
    tool_results: dict[str, Any]
    governance_flags: list[str]
    human_review_pending: bool
    current_node: str
    trace_steps: list[dict[str, Any]]
    final_output: dict[str, Any] | None
    error: str | None
