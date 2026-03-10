from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from core.schemas.base import AgentRequest, AgentResponse, AgentStatus


class LoanApprovalPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    applicant_id: str
    loan_amount: float = Field(gt=0)
    currency: str
    term_months: int = Field(gt=0)
    annual_income: float = Field(gt=0)
    credit_score: int = Field(ge=300, le=850)


class LoanApprovalResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: str
    approved_amount: float = Field(ge=0)
    apr_percent: float = Field(ge=0)
    rationale: str


class LoanApprovalRequest(AgentRequest):
    model_config = ConfigDict(extra="forbid", frozen=True)

    payload: LoanApprovalPayload


class LoanApprovalResponse(AgentResponse):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: AgentStatus
    output: LoanApprovalResult
