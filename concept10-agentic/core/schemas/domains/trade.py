from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from core.schemas.base import AgentRequest, AgentResponse, AgentStatus


class TradeApprovalPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    trader_id: str
    instrument: str
    side: str
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    venue: str


class TradeApprovalResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    approved: bool
    risk_score: float = Field(ge=0, le=1)
    required_overrides: list[str] = Field(default_factory=list)
    rationale: str


class TradeApprovalRequest(AgentRequest):
    model_config = ConfigDict(extra="forbid", frozen=True)

    payload: TradeApprovalPayload


class TradeApprovalResponse(AgentResponse):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: AgentStatus
    output: TradeApprovalResult
