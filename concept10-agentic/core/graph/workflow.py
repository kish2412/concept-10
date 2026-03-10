from __future__ import annotations

from datetime import UTC, datetime

from core.graph.state import OrchestrationState


async def run_orchestration(state: OrchestrationState) -> OrchestrationState:
    """Minimal async orchestration hook for non-graph execution paths."""
    state.setdefault("trace_steps", []).append(
        {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "node": "run_orchestration",
            "request_id": state.get("request_id", ""),
        }
    )
    state["current_node"] = "run_orchestration"
    return state
