from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class AgentStatus(str, Enum):
    success = "success"
    error = "error"
    pending = "pending"


class AgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_id: str
    session_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str
    agent_id: str
    status: AgentStatus
    output: dict[str, Any] = Field(default_factory=dict)
    trace_url: str | None = None
    duration_ms: float = Field(ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentError(AgentResponse):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: AgentStatus = AgentStatus.error
    error_code: str
    error_detail: str
    retry_after: float | None = Field(default=None, ge=0)
