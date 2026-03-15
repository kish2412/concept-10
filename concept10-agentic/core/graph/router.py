from __future__ import annotations

from core.graph.state import OrchestrationState

# Hard flags that should block execution
HARD_FAIL_FLAGS = {"prompt_injection_detected", "governance_guard_parse_failed", "toxicity_detected"}


def route_after_governance(state: OrchestrationState) -> str:
    governance_flags = state.get("governance_flags", [])
    # Only block if hard-fail flags are present
    if any(flag in HARD_FAIL_FLAGS for flag in governance_flags):
        return "block_with_error"
    return "llm_call"


def route_after_llm(state: OrchestrationState) -> str:
    tool_queue = state.get("context", {}).get("tool_queue", [])
    if tool_queue:
        return "tool_call"
    if state.get("human_review_pending"):
        return "human_review"
    return "final_output"


def route_after_human(state: OrchestrationState) -> str:
    decision = str(state.get("context", {}).get("human_decision", "")).lower()
    if decision in {"approved", "approve", "ok"}:
        return "approved"
    return "rejected"
