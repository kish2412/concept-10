from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Awaitable, Callable

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agents.registry.loader import AgentConfig, AgentRegistry
from core.graph.nodes import (
    make_governance_node,
    make_human_review_node,
    make_llm_node,
    make_telemetry_node,
    make_tool_node,
)
from core.graph.router import route_after_governance, route_after_human, route_after_llm
from core.graph.state import OrchestrationState

CompiledGraph = Any


class GraphBuilder:
    """Builds executable LangGraph workflows from registry agent configuration."""

    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    def build_for_agent(self, agent_config: AgentConfig) -> CompiledGraph:
        graph = StateGraph(OrchestrationState)

        llm_node = self._wrap_with_telemetry("llm_call", make_llm_node(agent_config))
        governance_node = self._wrap_with_telemetry(
            "governance",
            make_governance_node(agent_config.governance_profile),
        )

        graph.add_node("governance", governance_node)
        graph.add_node("llm_call", llm_node)
        graph.add_node("block_with_error", self._wrap_with_telemetry("block_with_error", self._block_with_error_node))
        graph.add_node("final_output", self._wrap_with_telemetry("final_output", self._final_output_node))

        graph.add_edge(START, "governance")
        graph.add_conditional_edges(
            "governance",
            route_after_governance,
            {
                "llm_call": "llm_call",
                "block_with_error": "block_with_error",
            },
        )

        tool_node_names: list[str] = []
        for index, tool_id in enumerate(agent_config.tools):
            tool_config = self.registry.get(tool_id)
            node_name = f"tool_call_{index}"
            graph.add_node(node_name, self._wrap_with_telemetry(node_name, make_tool_node(tool_config)))
            tool_node_names.append(node_name)

        if tool_node_names:
            human_review_target = "human_review" if agent_config.human_review_required else "final_output"
            graph.add_conditional_edges(
                "llm_call",
                route_after_llm,
                {
                    "tool_call": tool_node_names[0],
                    "human_review": human_review_target,
                    "final_output": "final_output",
                },
            )
            for idx, current_name in enumerate(tool_node_names):
                if idx < len(tool_node_names) - 1:
                    graph.add_edge(current_name, tool_node_names[idx + 1])
                elif agent_config.human_review_required:
                    graph.add_edge(current_name, "human_review")
                else:
                    graph.add_edge(current_name, "final_output")
        elif agent_config.human_review_required:
            graph.add_conditional_edges(
                "llm_call",
                route_after_llm,
                {
                    "tool_call": "final_output",
                    "human_review": "human_review",
                    "final_output": "final_output",
                },
            )
        else:
            graph.add_conditional_edges(
                "llm_call",
                route_after_llm,
                {
                    "tool_call": "final_output",
                    "human_review": "final_output",
                    "final_output": "final_output",
                },
            )

        if agent_config.human_review_required:
            graph.add_node("human_review", self._wrap_with_telemetry("human_review", make_human_review_node()))
            graph.add_conditional_edges(
                "human_review",
                route_after_human,
                {
                    "approved": "final_output",
                    "rejected": "block_with_error",
                },
            )

        graph.add_edge("final_output", END)
        graph.add_edge("block_with_error", END)

        return graph.compile(checkpointer=MemorySaver())

    def _wrap_with_telemetry(
        self,
        span_name: str,
        node_fn: Callable[[OrchestrationState], Awaitable[OrchestrationState]],
    ) -> Callable[[OrchestrationState], Awaitable[OrchestrationState]]:
        telemetry = make_telemetry_node(span_name)

        async def wrapped(state: OrchestrationState) -> OrchestrationState:
            state = await telemetry(state)
            state = await node_fn(state)
            state = await telemetry(state)
            return state

        return wrapped

    async def _block_with_error_node(self, state: OrchestrationState) -> OrchestrationState:
        state["error"] = state.get("error") or "Execution blocked by governance or review rejection"
        state["final_output"] = None
        state["current_node"] = "block_with_error"
        state.setdefault("trace_steps", []).append(
            {
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "node": "block_with_error",
                "request_id": state.get("request_id", ""),
                "error": state["error"],
            }
        )
        return state

    async def _final_output_node(self, state: OrchestrationState) -> OrchestrationState:
        llm_output = state.get("tool_results", {}).get("llm_call", {})
        state["final_output"] = {
            "agent_id": state.get("agent_id"),
            "request_id": state.get("request_id"),
            "llm_output": llm_output,
            "tool_results": state.get("tool_results", {}),
        }
        state["current_node"] = "final_output"
        state["error"] = None
        state.setdefault("trace_steps", []).append(
            {
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "node": "final_output",
                "request_id": state.get("request_id", ""),
                "status": "success",
            }
        )
        return state
