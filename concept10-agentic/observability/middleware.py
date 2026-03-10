from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from observability.langsmith_config import TraceContext
from observability.logging import get_logger
from observability.tracking import request_tracker

LOGGER = get_logger(__name__)


class RequestTrackerMiddleware(BaseHTTPMiddleware):
    """Attach and propagate X-Request-ID using RequestTracker."""

    async def dispatch(self, request: Request, call_next):
        category = request.headers.get("X-Agent-Category") or request.query_params.get("agent_category") or "orchestrator"
        request_tracker.set_agent_category(category)
        request_id = request.headers.get("X-Request-ID") or request_tracker.generate_request_id()
        request_tracker.set_request_id(request_id)

        agent_id = (
            request.headers.get("X-Agent-ID")
            or request.path_params.get("agent_id")
            or request.query_params.get("agent_id")
            or "unknown-agent"
        )

        request.state.request_id = request_id
        request.state.agent_id = agent_id

        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class LangSmithMiddleware(BaseHTTPMiddleware):
    """Initialize per-request LangSmith TraceContext lifecycle."""

    async def dispatch(self, request: Request, call_next):
        request_id = getattr(request.state, "request_id", "") or request_tracker.get_request_id()
        agent_id = (
            getattr(request.state, "agent_id", "")
            or request.headers.get("X-Agent-ID")
            or request.path_params.get("agent_id")
            or request.query_params.get("agent_id")
            or "unknown-agent"
        )

        async with TraceContext(request_id=request_id, agent_id=agent_id, project=None) as trace_ctx:
            request.state.trace_context = trace_ctx
            trace_ctx.set_metadata("path", request.url.path)
            trace_ctx.set_metadata("method", request.method)
            trace_ctx.set_metadata("request_id", request_id)
            trace_ctx.add_tag("http")

            LOGGER.info("request_trace", agent_id=agent_id, request_id=request_id)

            try:
                response: Response = await call_next(request)
            except Exception as exc:
                trace_ctx.set_metadata("status", "exception")
                trace_ctx.set_outputs({"error": str(exc)})
                raise

            response.headers["X-Request-ID"] = request_id
            trace_ctx.set_outputs({"status_code": response.status_code})
            trace_ctx.set_metadata("status", "ok")
            return response


class RequestTracingMiddleware(RequestTrackerMiddleware):
    """Backward-compatible alias kept for older imports."""
