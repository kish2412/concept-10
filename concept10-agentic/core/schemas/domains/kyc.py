from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from core.schemas.base import AgentRequest, AgentResponse, AgentStatus


class KYCCheckPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    customer_id: str
    country_code: str = Field(min_length=2, max_length=2)
    document_type: str
    document_number: str


class KYCCheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kyc_passed: bool
    risk_level: str
    matched_watchlists: list[str] = Field(default_factory=list)
    rationale: str


class KYCCheckRequest(AgentRequest):
    model_config = ConfigDict(extra="forbid", frozen=True)

    payload: KYCCheckPayload


class KYCCheckResponse(AgentResponse):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: AgentStatus
    output: KYCCheckResult
