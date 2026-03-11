from __future__ import annotations

import asyncio
from contextlib import contextmanager

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from observability.logging import add_request_id, configure_logging, get_logger
from observability.middleware import RequestTrackerMiddleware
from core.graph.nodes import make_telemetry_node
from observability.tracking import request_tracker


@pytest.mark.asyncio
async def test_tracking_propagates_request_id_to_header_state_and_log(caplog):
    configure_logging()

    app = FastAPI()
    app.add_middleware(RequestTrackerMiddleware)

    @app.get("/echo")
    async def echo(request: Request):
        logger = get_logger("tracking-test")
        logger.info("inside_handler")
        event = add_request_id(None, "info", {"event": "inside_handler"})
        return {"request_id": request.state.request_id, "event": event}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/echo", headers={"X-Request-ID": "orch-fixed-id"})

    body = response.json()

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "orch-fixed-id"
    assert body["request_id"] == "orch-fixed-id"
    assert body["event"]["request_id"] == "orch-fixed-id"


@pytest.mark.asyncio
async def test_tracking_sets_mock_otel_span_attributes(monkeypatch):
    captured_attributes: dict[str, str] = {}

    class FakeSpan:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def set_attribute(self, key, value):
            captured_attributes[key] = value

    class FakeTracer:
        @contextmanager
        def start_as_current_span(self, _name):
            yield FakeSpan()

    monkeypatch.setattr("opentelemetry.trace.get_tracer", lambda _name: FakeTracer())

    request_tracker.set_request_id("orch-span-test")
    node = make_telemetry_node("span-node")

    state = {
        "request_id": "orch-span-test",
        "session_id": "s-1",
        "agent_id": "test-orchestrator",
        "messages": [],
        "context": {},
        "tool_results": {},
        "governance_flags": [],
        "human_review_pending": False,
        "current_node": "start",
        "trace_steps": [],
        "final_output": None,
        "error": None,
    }

    await node(state)

    assert captured_attributes["request_id"] == "orch-span-test"
    assert captured_attributes["agent.request_id"] == "orch-span-test"
    assert captured_attributes["agent_id"] == "test-orchestrator"
