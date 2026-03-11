from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.schemas.base import AgentStatus
from core.schemas.validators import SchemaValidator


@pytest.mark.asyncio
async def test_schema_validator_validates_input_and_output(mock_registry):
    validator = SchemaValidator()
    cfg = mock_registry.get("test-orchestrator")

    request_obj = validator.validate_input(
        cfg,
        {
            "request_id": "req-1",
            "agent_id": "test-orchestrator",
            "session_id": "session-1",
            "payload": {"task": "do work"},
            "metadata": {},
            "created_at": datetime.now(UTC),
        },
    )
    assert request_obj.agent_id == "test-orchestrator"

    response_obj = validator.validate_output(
        cfg,
        {
            "request_id": "req-1",
            "agent_id": "test-orchestrator",
            "status": AgentStatus.success,
            "output": {"ok": True},
            "trace_url": None,
            "duration_ms": 12.5,
            "created_at": datetime.now(UTC),
        },
    )
    assert response_obj.status == AgentStatus.success


@pytest.mark.asyncio
async def test_schema_validator_rejects_extra_fields(mock_registry):
    validator = SchemaValidator()
    cfg = mock_registry.get("test-orchestrator")

    with pytest.raises(Exception):
        validator.validate_input(
            cfg,
            {
                "request_id": "req-1",
                "agent_id": "test-orchestrator",
                "session_id": "session-1",
                "payload": {},
                "metadata": {},
                "created_at": datetime.now(UTC),
                "extra": "not-allowed",
            },
        )

    with pytest.raises(Exception):
        validator.validate_output(
            cfg,
            {
                "request_id": "req-1",
                "agent_id": "test-orchestrator",
                "status": AgentStatus.success,
                "output": {},
                "trace_url": None,
                "duration_ms": 1.0,
                "created_at": datetime.now(UTC),
                "extra": "not-allowed",
            },
        )
