from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any, AsyncGenerator, TypedDict

from agents.registry.loader import AgentRegistry
from core.context.manager import ContextManager
from core.graph.builder import CompiledGraph, GraphBuilder
from core.graph.state import OrchestrationState
from core.prompts.template_loader import PromptLoader
from core.schemas.base import AgentError, AgentRequest, AgentResponse, AgentStatus
from observability.tracking import request_tracker


class StateChunk(TypedDict):
    event: str
    data: dict[str, Any]


class GraphExecutor:
    def __init__(self, registry: AgentRegistry, context_manager: ContextManager):
        self.registry = registry
        self.context_manager = context_manager
        self.graph_builder = GraphBuilder(registry)
        self.prompt_loader = PromptLoader()
        self._graph_cache: dict[tuple[str, str], CompiledGraph] = {}
        self._graph_cache_lock = threading.RLock()

    async def execute(self, request: AgentRequest) -> AgentResponse:
        started_at = datetime.now(UTC)
        request = self._ensure_request_id(request)
        request_tracker.set_request_id(str(request.request_id))

        try:
            agent_config = await self._load_agent_config(request.agent_id)
            system_prompt = self.prompt_loader.render_system(
                agent_config,
                {
                    **request.payload,
                    "request_id": str(request.request_id),
                    "task": request.payload.get("task", ""),
                },
            )

            state = self._initialize_state(request, system_prompt)
            compiled = self._get_or_build_graph(agent_config.id, agent_config.version, agent_config)

            final_state: OrchestrationState | None = None
            async for chunk in self.stream_execute(request):
                if chunk["event"] == "state":
                    final_state = chunk["data"].get("state")  # type: ignore[assignment]
                elif chunk["event"] == "error":
                    error_detail = str(chunk["data"].get("error", "graph_execution_failed"))
                    return self._build_error_response(
                        request=request,
                        started_at=started_at,
                        error_code="GRAPH_EXECUTION_ERROR",
                        error_detail=error_detail,
                        trace_url=self._resolve_trace_url(str(request.request_id)),
                    )

            if final_state is None:
                return self._build_error_response(
                    request=request,
                    started_at=started_at,
                    error_code="EMPTY_GRAPH_RESULT",
                    error_detail="Graph execution finished without a final state",
                    trace_url=self._resolve_trace_url(str(request.request_id)),
                )

            if final_state.get("error"):
                return self._build_error_response(
                    request=request,
                    started_at=started_at,
                    error_code="NODE_EXECUTION_ERROR",
                    error_detail=str(final_state["error"]),
                    trace_url=self._resolve_trace_url(str(request.request_id)),
                )

            return AgentResponse(
                request_id=request.request_id,
                agent_id=request.agent_id,
                status=AgentStatus.success,
                output=final_state.get("final_output") or {},
                trace_url=self._resolve_trace_url(str(request.request_id)),
                duration_ms=self._duration_ms(started_at),
                created_at=datetime.now(UTC),
            )
        except Exception as exc:
            return self._build_error_response(
                request=request,
                started_at=started_at,
                error_code="EXECUTOR_ERROR",
                error_detail=str(exc),
                trace_url=self._resolve_trace_url(str(request.request_id)),
            )

    async def stream_execute(self, request: AgentRequest) -> AsyncGenerator[StateChunk, None]:
        request = self._ensure_request_id(request)
        request_tracker.set_request_id(str(request.request_id))
        state: OrchestrationState | None = None
        try:
            agent_config = await self._load_agent_config(request.agent_id)

            system_prompt = self.prompt_loader.render_system(
                agent_config,
                {
                    **request.payload,
                    "request_id": str(request.request_id),
                    "task": request.payload.get("task", ""),
                },
            )

            state = self._initialize_state(request, system_prompt)
            compiled = self._get_or_build_graph(agent_config.id, agent_config.version, agent_config)

            yield {
                "event": "start",
                "data": {
                    "request_id": str(request.request_id),
                    "agent_id": request.agent_id,
                },
            }

            async for update in compiled.astream(
                state,
                config={"configurable": {"thread_id": str(request.request_id)}},
                stream_mode="updates",
            ):
                state = self._merge_state_update(state, update)
                yield {
                    "event": "chunk",
                    "data": {
                        "request_id": str(request.request_id),
                        "update": update,
                        "trace_steps": state.get("trace_steps", []),
                    },
                }

            yield {
                "event": "state",
                "data": {
                    "request_id": str(request.request_id),
                    "state": state,
                },
            }
        except Exception as exc:
            if state is None:
                state = {
                    "request_id": str(request.request_id),
                    "session_id": request.session_id,
                    "agent_id": request.agent_id,
                    "messages": [],
                    "context": dict(request.payload),
                    "tool_results": {},
                    "governance_flags": [],
                    "human_review_pending": False,
                    "current_node": "executor.stream_execute",
                    "trace_steps": [],
                    "final_output": None,
                    "error": None,
                }
            state["error"] = str(exc)
            state.setdefault("trace_steps", []).append(
                {
                    "timestamp_utc": datetime.now(UTC).isoformat(),
                    "node": "executor.stream_execute",
                    "request_id": str(request.request_id),
                    "error": str(exc),
                }
            )
            yield {
                "event": "error",
                "data": {
                    "request_id": str(request.request_id),
                    "error": str(exc),
                    "state": state,
                },
            }

    async def _load_agent_config(self, agent_id: str):
        try:
            return self.registry.get(agent_id)
        except KeyError:
            await self.registry.load()
            return self.registry.get(agent_id)

    def _get_or_build_graph(self, agent_id: str, agent_version: str, agent_config) -> CompiledGraph:
        key = (agent_id, agent_version)
        with self._graph_cache_lock:
            if key in self._graph_cache:
                return self._graph_cache[key]

            compiled = self.graph_builder.build_for_agent(agent_config)
            self._graph_cache[key] = compiled
            return compiled

    def _initialize_state(self, request: AgentRequest, system_prompt: str) -> OrchestrationState:
        runtime_context = self.context_manager.build_runtime_context(
            request_id=str(request.request_id),
            metadata=request.metadata,
        )
        runtime_context.update(request.payload)
        runtime_context["system_prompt"] = system_prompt
        runtime_context.setdefault("task", request.payload.get("task", ""))
        runtime_context.setdefault("tool_queue", [])

        return {
            "request_id": str(request.request_id),
            "session_id": request.session_id,
            "agent_id": request.agent_id,
            "messages": [],
            "context": runtime_context,
            "tool_results": {},
            "governance_flags": [],
            "human_review_pending": False,
            "current_node": "start",
            "trace_steps": [],
            "final_output": None,
            "error": None,
        }

    def _merge_state_update(self, state: OrchestrationState, update: Any) -> OrchestrationState:
        if not isinstance(update, dict):
            return state

        for _, payload in update.items():
            if isinstance(payload, dict):
                for key, value in payload.items():
                    if key == "trace_steps" and isinstance(value, list):
                        state.setdefault("trace_steps", []).extend(value)
                    elif key in state:
                        state[key] = value  # type: ignore[index]
        return state

    def _build_error_response(
        self,
        request: AgentRequest,
        started_at: datetime,
        error_code: str,
        error_detail: str,
        trace_url: str | None,
    ) -> AgentError:
        return AgentError(
            request_id=request.request_id,
            agent_id=request.agent_id,
            output={},
            trace_url=trace_url,
            duration_ms=self._duration_ms(started_at),
            created_at=datetime.now(UTC),
            error_code=error_code,
            error_detail=error_detail,
            retry_after=None,
        )

    def _resolve_trace_url(self, request_id: str) -> str | None:
        builder = getattr(self.context_manager, "build_trace_url", None)
        if callable(builder):
            value = builder(request_id)
            if isinstance(value, str) and value:
                return value
        return None

    @staticmethod
    def _duration_ms(started_at: datetime) -> float:
        return (datetime.now(UTC) - started_at).total_seconds() * 1000.0

    @staticmethod
    def _ensure_request_id(request: AgentRequest) -> AgentRequest:
        if getattr(request, "request_id", None):
            return request
        return request.model_copy(update={"request_id": request_tracker.generate_request_id()})
