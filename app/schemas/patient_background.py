import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PatientBackgroundUpdate(BaseModel):
    medical_history: str | None = None
    surgical_history: str | None = None
    family_history: str | None = None
    social_history: str | None = None
    current_medications: str | None = None
    immunizations: dict = Field(default_factory=dict)


class PatientBackgroundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clinic_id: uuid.UUID
    patient_id: uuid.UUID
    medical_history: str | None
    surgical_history: str | None
    family_history: str | None
    social_history: str | None
    current_medications: str | None
    immunizations: dict
    created_at: datetime
    updated_at: datetime
    is_deleted: bool