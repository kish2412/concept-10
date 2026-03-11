from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from api.app import app
from core.schemas.base import AgentResponse, AgentStatus


class StubExecutor:
    async def execute(self, request):
        return AgentResponse(
            request_id=request.request_id,
            agent_id=request.agent_id,
            status=AgentStatus.success,
            output={"ok": True},
            trace_url=None,
            duration_ms=1.0,
            created_at=datetime.now(UTC),
        )

    async def stream_execute(self, _request):
        if False:
            yield


@pytest.mark.asyncio
async def test_api_orchestrate_endpoint_success(mock_registry):
    app.state.registry = mock_registry
    app.state.executor = StubExecutor()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/orchestrate/test-orchestrator",
            json={
                "request_id": "req-1",
                "agent_id": "test-orchestrator",
                "session_id": "s-1",
                "payload": {"task": "do work"},
                "metadata": {},
                "created_at": datetime.now(UTC).isoformat(),
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.headers.get("X-Request-ID")


@pytest.mark.asyncio
async def test_api_orchestrate_unknown_agent_returns_404(mock_registry):
    app.state.registry = mock_registry
    app.state.executor = StubExecutor()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/orchestrate/missing-agent",
            json={
                "request_id": "req-2",
                "agent_id": "missing-agent",
                "session_id": "s-2",
                "payload": {"task": "do work"},
                "metadata": {},
                "created_at": datetime.now(UTC).isoformat(),
            },
        )

    assert response.status_code == 404
