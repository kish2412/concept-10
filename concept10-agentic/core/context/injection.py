from __future__ import annotations

from typing import Any

from core.graph.state import OrchestrationState


def inject_context_into_state(state: OrchestrationState, ctx_manager: Any) -> OrchestrationState:
    """Enrich state.context with session-aware conversational context before node execution."""
    session_id = state.get("session_id", "")
    if not session_id:
        return state

    context = state.setdefault("context", {})
    agent_config = context.get("agent_config")

    if agent_config is not None and hasattr(ctx_manager, "get_context"):
        messages = ctx_manager.get_context(session_id, agent_config)
        state["messages"] = messages
        context["messages"] = messages

    if hasattr(ctx_manager, "get_session_stats"):
        context["session_stats"] = ctx_manager.get_session_stats(session_id)

    return state
