from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from core.context.manager import ContextManager


def test_context_manager_sliding_window_preserves_system_and_pinned(monkeypatch, mock_registry):
    manager = ContextManager()
    cfg = mock_registry.get("test-orchestrator")
    cfg = cfg.model_copy(update={"max_context_tokens": 20})

    monkeypatch.setattr(
        manager,
        "_count_message_tokens",
        lambda message, _model_name: max(1, len(str(message.content)) // 10),
    )

    session_id = "s-1"
    manager.add_message(session_id, SystemMessage(content="system-instruction"))
    manager.add_message(
        session_id,
        HumanMessage(content="pinned-msg", additional_kwargs={"metadata": {"pinned": True}}),
    )
    manager.add_message(session_id, HumanMessage(content="old message one"))
    manager.add_message(session_id, HumanMessage(content="newest message two"))

    selected = manager.get_context(session_id, cfg)
    contents = [str(item.content) for item in selected]

    assert "system-instruction" in contents
    assert "pinned-msg" in contents
    assert any("newest" in content for content in contents)


@pytest.mark.asyncio
async def test_context_manager_triggers_compression(monkeypatch, mock_registry):
    manager = ContextManager()
    cfg = mock_registry.get("test-orchestrator")

    monkeypatch.setenv("CONTEXT_DEFAULT_MAX_TOKENS", "10")
    monkeypatch.setattr(manager, "_count_message_tokens", lambda _m, _n: 5)

    session_id = "compress-me"
    manager.add_message(session_id, SystemMessage(content="sys"))
    manager.add_message(session_id, HumanMessage(content="m1"))
    manager.add_message(session_id, HumanMessage(content="m2"))
    manager.add_message(session_id, HumanMessage(content="m3"))
    manager.add_message(session_id, HumanMessage(content="m4"))

    await manager.summarise_and_compress(session_id)

    stats = manager.get_session_stats(session_id)
    messages = manager.get_context(session_id, cfg)
    contents = [str(msg.content) for msg in messages]

    assert stats["compression_count"] >= 1
    assert any("[COMPRESSED_CONTEXT]" in content for content in contents)
