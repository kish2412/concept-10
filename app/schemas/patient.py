import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    blood_type: str | None = None
    allergies: list[str] = Field(default_factory=list)
    is_active: bool = True


class PatientUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    blood_type: str | None = None
    allergies: list[str] | None = None
    is_active: bool | None = None


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clinic_id: uuid.UUID
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    phone: str | None
    email: EmailStr | None
    address: str | None
    blood_type: str | None
    allergies: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    is_deleted: bool


class PatientListResponse(BaseModel):
    items: list[PatientResponse]
    page: int
    size: int
    total: int
