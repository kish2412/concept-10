import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class PatientBackground(BaseModel):
    __tablename__ = "patient_backgrounds"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    medical_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    surgical_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    family_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    social_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_medications: Mapped[str | None] = mapped_column(Text, nullable=True)
    immunizations: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")

    patient = relationship("Patient", back_populates="background", lazy="joined")
