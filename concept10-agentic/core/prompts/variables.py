from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SystemPromptVariables(BaseModel):
    """Variables injected into every system prompt template."""

    agent_id: str
    request_id: str
    timestamp_utc: datetime
    compliance_mode: str = Field(default="standard")
    user_tier: str = Field(default="standard")
