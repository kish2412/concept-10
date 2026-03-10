from __future__ import annotations

import time
from functools import wraps
from typing import Any, Awaitable, Callable, ParamSpec, TypeVar

from opentelemetry import trace

from observability.tracking import request_tracker

P = ParamSpec("P")
R = TypeVar("R")


def _extract_agent_meta(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, str]:
    state = kwargs.get("state")
    agent_id = kwargs.get("agent_id", "")
    category = kwargs.get("category", "")
    node_name = kwargs.get("node_name", "")

    if isinstance(state, dict):
        agent_id = agent_id or str(state.get("agent_id", ""))
        node_name = node_name or str(state.get("current_node", ""))

    agent_config = kwargs.get("agent_config")
    if agent_config is not None:
        agent_id = agent_id or str(getattr(agent_config, "id", ""))
        category = category or str(getattr(agent_config, "category", ""))

    if args:
        first = args[0]
        if isinstance(first, dict):
            agent_id = agent_id or str(first.get("agent_id", ""))
            node_name = node_name or str(first.get("current_node", ""))

    return {
        "agent_id": agent_id,
        "category": category,
        "node_name": node_name,
    }


def agent_span(name: str) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            tracer = trace.get_tracer("concept10-agentic")
            with tracer.start_as_current_span(name) as span:
                request_id = request_tracker.get_request_id()
                meta = _extract_agent_meta(args, kwargs)
                span.set_attribute("agent.request_id", request_id)
                span.set_attribute("agent.agent_id", meta["agent_id"])
                span.set_attribute("agent.category", meta["category"])
                span.set_attribute("agent.node_name", meta["node_name"])
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    span.record_exception(exc)
                    raise

        return wrapper

    return decorator


def governance_span(validator_name: str) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            tracer = trace.get_tracer("concept10-agentic")
            span_name = f"governance::{validator_name}"
            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute("governance.validator", validator_name)
                span.set_attribute("agent.request_id", request_tracker.get_request_id())
                try:
                    result = await func(*args, **kwargs)
                    if isinstance(result, dict):
                        span.set_attribute("governance.result", str(result.get("result", "success")))
                        flags = result.get("flags", [])
                        span.set_attribute("governance.flags", str(flags))
                    return result
                except Exception as exc:
                    span.set_attribute("governance.result", "error")
                    span.record_exception(exc)
                    raise

        return wrapper

    return decorator


def llm_span(model: str) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            tracer = trace.get_tracer("concept10-agentic")
            with tracer.start_as_current_span("llm.call") as span:
                start = time.perf_counter()
                span.set_attribute("llm.model", model)
                span.set_attribute("agent.request_id", request_tracker.get_request_id())
                try:
                    result = await func(*args, **kwargs)
                    usage = {}
                    if isinstance(result, dict):
                        usage = result.get("usage", {}) if isinstance(result.get("usage"), dict) else {}
                    prompt_tokens = int(usage.get("prompt_tokens", 0))
                    completion_tokens = int(usage.get("completion_tokens", 0))
                    span.set_attribute("llm.prompt_tokens", prompt_tokens)
                    span.set_attribute("llm.completion_tokens", completion_tokens)
                    span.set_attribute("llm.latency_ms", (time.perf_counter() - start) * 1000.0)
                    return result
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_attribute("llm.latency_ms", (time.perf_counter() - start) * 1000.0)
                    raise

        return wrapper

    return decorator


def get_trace_id() -> str:
    span = trace.get_current_span()
    span_ctx = span.get_span_context()
    if not span_ctx or not span_ctx.trace_id:
        return ""
    return f"{span_ctx.trace_id:032x}"
