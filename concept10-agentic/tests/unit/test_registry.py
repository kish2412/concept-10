from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_registry_load_get_and_list_by_category(mock_registry):
    loaded = mock_registry.list_all()
    assert len(loaded) == 2

    agent = mock_registry.get("test-orchestrator")
    assert agent.id == "test-orchestrator"
    assert agent.category == "orchestrator"

    utilities = mock_registry.list_by_category("utility")
    assert [item.id for item in utilities] == ["test-utility"]


@pytest.mark.asyncio
async def test_registry_get_unknown_raises_keyerror(mock_registry):
    with pytest.raises(KeyError):
        mock_registry.get("missing-agent")
