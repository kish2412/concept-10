import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Patient(BaseModel):
    __tablename__ = "patients"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    blood_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    allergies: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list, server_default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    background = relationship("PatientBackground", back_populates="patient", uselist=False, lazy="selectin")
