from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
import yaml
from httpx import Response

from agents.registry.loader import AgentRegistry
from core.schemas.base import AgentRequest


@pytest_asyncio.fixture
async def mock_registry(tmp_path: Path) -> AgentRegistry:
    templates_dir = tmp_path / "core" / "prompts" / "templates"
    rails_dir = tmp_path / "core" / "governance" / "rail_specs"
    templates_dir.mkdir(parents=True, exist_ok=True)
    rails_dir.mkdir(parents=True, exist_ok=True)

    (templates_dir / "orchestrator.j2").write_text(
        "Agent={{ agent_id }} Request={{ request_id }} Task={{ task }}",
        encoding="utf-8",
    )
    (templates_dir / "utility.j2").write_text(
        "Utility Agent={{ agent_id }} Request={{ request_id }}",
        encoding="utf-8",
    )
    (rails_dir / "orchestrator.rail").write_text("# rail", encoding="utf-8")
    (rails_dir / "utility.rail").write_text("# rail", encoding="utf-8")

    registry_payload = {
        "version": 1,
        "agents": [
            {
                "id": "test-orchestrator",
                "category": "orchestrator",
                "version": "1.0.0",
                "description": "Test orchestrator",
                "prompt_template": "core/prompts/templates/orchestrator.j2",
                "input_schema": "core.schemas.base.AgentRequest",
                "output_schema": "core.schemas.base.AgentResponse",
                "tags": ["test"],
                "tools": ["test-utility"],
                "governance_profile": "core/governance/rail_specs/orchestrator.rail",
                "langsmith_project": "test-project",
                "otel_service_name": "agent.test.orchestrator",
                "human_review_required": False,
                "max_context_tokens": 2048,
            },
            {
                "id": "test-utility",
                "category": "utility",
                "version": "1.0.0",
                "description": "Test utility",
                "prompt_template": "core/prompts/templates/utility.j2",
                "input_schema": "core.schemas.base.AgentRequest",
                "output_schema": "core.schemas.base.AgentResponse",
                "tags": ["test"],
                "tools": [],
                "governance_profile": "core/governance/rail_specs/utility.rail",
                "langsmith_project": "test-project",
                "otel_service_name": "agent.test.utility",
                "human_review_required": False,
                "max_context_tokens": 1024,
            },
        ],
    }

    registry_path = tmp_path / "agents" / "registry"
    registry_path.mkdir(parents=True, exist_ok=True)
    yaml_path = registry_path / "agent_registry.yaml"
    yaml_path.write_text(yaml.safe_dump(registry_payload, sort_keys=False), encoding="utf-8")

    registry = AgentRegistry(registry_path=str(yaml_path), project_root=str(tmp_path))
    await registry.load()
    return registry


@pytest.fixture
def sample_agent_request() -> AgentRequest:
    return AgentRequest(
        request_id="req-123",
        agent_id="test-orchestrator",
        session_id="session-123",
        payload={"task": "evaluate application", "tool_queue": ["test-utility"]},
        metadata={"source": "pytest"},
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_llm(respx_mock):
    route = respx_mock.post("https://llm.mock.local/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={
                "choices": [{"message": {"content": "mocked llm response"}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 5},
            },
        )
    )

    async def _call(*, prompt: str, state: dict):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://llm.mock.local/v1/chat/completions",
                json={"prompt": prompt, "request_id": state.get("request_id")},
            )
            response.raise_for_status()
            payload = response.json()
            return {
                "response": payload["choices"][0]["message"]["content"],
                "usage": payload.get("usage", {}),
            }

    _call.route = route
    return _call
