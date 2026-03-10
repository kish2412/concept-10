import pytest

from agents.registry.loader import load_agent_registry


@pytest.mark.asyncio
async def test_registry_loads() -> None:
    data = await load_agent_registry("agents/registry/agent_registry.yaml")
    assert "agents" in data
