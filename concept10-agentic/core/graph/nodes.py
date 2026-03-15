from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Awaitable, Callable

from agents.registry.loader import AgentConfig
from core.governance.governance_node import make_governance_node as make_guardrail_governance_node
from core.graph.state import OrchestrationState
from core.prompts.template_loader import PromptLoader

logger = logging.getLogger(__name__)


async def _resolve_maybe_async(value: Any) -> Any:
    if hasattr(value, "__await__"):
        return await value
    return value


def make_llm_node(agent_config: AgentConfig) -> Callable[[OrchestrationState], Awaitable[OrchestrationState]]:
    prompt_loader = PromptLoader()

    async def llm_node(state: OrchestrationState) -> OrchestrationState:
        runtime_ctx = {
            **state.get("context", {}),
            "request_id": state["request_id"],
            "task": state.get("context", {}).get("task", ""),
        }
        prompt = str(state.get("context", {}).get("system_prompt", ""))
        if not prompt:
            prompt = prompt_loader.render_system(agent_config, runtime_ctx)

        llm_callable = state.get("context", {}).get("llm_callable")
        if callable(llm_callable):
            llm_result = await _resolve_maybe_async(llm_callable(prompt=prompt, state=state))
        else:
            # Create LLM callable from configuration
            try:
                import os
                from langchain_openai import ChatOpenAI
                from langchain_core.output_parsers import JsonOutputParser
                from langchain_core.messages import SystemMessage

                api_key = os.getenv("OPENAI_API_KEY")
                model_name = os.getenv("DEFAULT_AGENT_MODEL", "gpt-4o")

                if not api_key:
                    logger.warning("OPENAI_API_KEY not configured, returning fallback response")
                    llm_result = {"response": prompt[:800]}
                else:
                    llm = ChatOpenAI(api_key=api_key, model=model_name, temperature=0.7)
                    parser = JsonOutputParser()
                    chain = llm | parser

                    try:
                        # Pass a list of BaseMessages (SystemMessage) instead of a dict
                        llm_result = await chain.ainvoke([SystemMessage(content=prompt)])
                    except Exception as llm_err:
                        logger.error(f"LLM call failed: {llm_err}", exc_info=True)
                        llm_result = {"response": "LLM call failed"}
            except ImportError:
                logger.warning("langchain_openai not available, returning fallback response")
                llm_result = {"response": prompt[:800]}

        state.setdefault("tool_results", {})["llm_call"] = llm_result
        state.setdefault("trace_steps", []).append(
            {
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "node": "llm_call",
                "request_id": state["request_id"],
                "status": "success",
            }
        )
        state["current_node"] = "llm_call"
        return state

    return llm_node


def make_tool_node(tool_config: AgentConfig) -> Callable[[OrchestrationState], Awaitable[OrchestrationState]]:
    async def tool_node(state: OrchestrationState) -> OrchestrationState:
        result = {
            "tool_id": tool_config.id,
            "category": tool_config.category,
            "status": "executed",
        }
        state.setdefault("tool_results", {})[tool_config.id] = result
        state.setdefault("trace_steps", []).append(
            {
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "node": f"tool:{tool_config.id}",
                "request_id": state["request_id"],
                "status": "success",
            }
        )
        state["current_node"] = f"tool:{tool_config.id}"
        return state

    return tool_node


def make_governance_node(rail_spec: str) -> Callable[[OrchestrationState], Awaitable[OrchestrationState]]:
    agent_id = Path(rail_spec).stem

    # Fallback shim: if no exact agent id exists, use current state agent during execution.
    async def fallback_governance_node(state: OrchestrationState) -> OrchestrationState:
        from agents.registry.loader import AgentRegistry

        registry = AgentRegistry()
        await registry.load()
        try:
            cfg = registry.get(state.get("agent_id", agent_id))
        except KeyError:
            cfg = registry.list_by_category("orchestrator")[0]
        node = make_guardrail_governance_node(cfg)
        return await node(state)

    return fallback_governance_node


def make_human_review_node() -> Callable[[OrchestrationState], Awaitable[OrchestrationState]]:
    async def human_review_node(state: OrchestrationState) -> OrchestrationState:
        state["human_review_pending"] = True
        state.setdefault("trace_steps", []).append(
            {
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "node": "human_review",
                "request_id": state["request_id"],
                "status": "pending",
            }
        )
        state["current_node"] = "human_review"
        return state

    return human_review_node


def make_telemetry_node(span_name: str) -> Callable[[OrchestrationState], Awaitable[OrchestrationState]]:
    async def telemetry_node(state: OrchestrationState) -> OrchestrationState:
        try:
            from opentelemetry import trace  # type: ignore

            tracer = trace.get_tracer("concept10-agentic")
            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute("request_id", state.get("request_id", ""))
                span.set_attribute("agent.request_id", state.get("request_id", ""))
                span.set_attribute("agent_id", state.get("agent_id", ""))
        except Exception:
            # Telemetry should never break execution flow.
            pass

        state.setdefault("trace_steps", []).append(
            {
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "node": f"telemetry:{span_name}",
                "request_id": state.get("request_id", ""),
                "status": "recorded",
            }
        )
        return state

    return telemetry_node
