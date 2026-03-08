from pydantic import BaseModel, Field


class ClinicAISettingsResponse(BaseModel):
    ai_enabled: bool
    ai_policy_tier: str | None = None
    ai_guardrail_profile: str | None = None


class ClinicAISettingsUpdate(BaseModel):
    ai_enabled: bool | None = None
    ai_policy_tier: str | None = Field(default=None, max_length=50)
    ai_guardrail_profile: str | None = Field(default=None, max_length=100)
