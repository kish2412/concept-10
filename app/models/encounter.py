import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


# ──────────────────────────────────────────────────────────────────────
# 1. Encounter
# ──────────────────────────────────────────────────────────────────────
class Encounter(BaseModel):
    __tablename__ = "encounters"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    encounter_id: Mapped[str] = mapped_column(
        String(30), nullable=False, unique=True, index=True,
    )  # human-readable: ENC-YYYYMMDD-XXXX
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
    )
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )

    # Enums stored as constrained strings
    encounter_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="CONSULTATION",
    )  # CONSULTATION | FOLLOW_UP | EMERGENCY | PROCEDURE | TELECONSULT
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="SCHEDULED", index=True,
    )  # SCHEDULED | CHECKED_IN | TRIAGE | WITH_PROVIDER | PENDING_RESULTS
    #    PENDING_REVIEW | DISCHARGED | CANCELLED | NO_SHOW

    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Persisted AI triage summary payload (latest generation)
    ai_triage_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_triage_focus_points: Mapped[list | dict | None] = mapped_column(JSONB, nullable=True)
    ai_triage_red_flags: Mapped[list | dict | None] = mapped_column(JSONB, nullable=True)
    ai_triage_missing_information: Mapped[list | dict | None] = mapped_column(JSONB, nullable=True)
    ai_triage_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_triage_orchestration: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ai_triage_model_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ai_triage_model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ai_triage_guardrail_profile: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Timestamps
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True,
    )
    checked_in_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    triage_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # Audit
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )

    # Soft-delete override — use deleted_at timestamp instead of bool
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # Relationships
    patient = relationship("Patient", lazy="selectin")
    vitals = relationship(
        "EncounterVitals", back_populates="encounter",
        cascade="all, delete-orphan", lazy="selectin",
    )
    notes = relationship(
        "EncounterNote", back_populates="encounter",
        cascade="all, delete-orphan", lazy="selectin",
    )
    diagnoses = relationship(
        "EncounterDiagnosis", back_populates="encounter",
        cascade="all, delete-orphan", lazy="selectin",
    )
    orders = relationship(
        "EncounterOrder", back_populates="encounter",
        cascade="all, delete-orphan", lazy="selectin",
    )
    medications = relationship(
        "EncounterMedication", back_populates="encounter",
        cascade="all, delete-orphan", lazy="selectin",
    )
    disposition = relationship(
        "EncounterDisposition", back_populates="encounter",
        uselist=False, cascade="all, delete-orphan", lazy="selectin",
    )


# ──────────────────────────────────────────────────────────────────────
# 2. EncounterVitals
# ──────────────────────────────────────────────────────────────────────
class EncounterVitals(BaseModel):
    __tablename__ = "encounter_vitals"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("encounters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    blood_pressure_systolic: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    blood_pressure_diastolic: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    pulse_rate: Mapped[float | None] = mapped_column(
        Numeric(5, 1), nullable=True,
    )
    respiratory_rate: Mapped[float | None] = mapped_column(
        Numeric(5, 1), nullable=True,
    )
    temperature: Mapped[float | None] = mapped_column(
        Numeric(4, 1), nullable=True,
    )
    oxygen_saturation: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True,
    )
    weight: Mapped[float | None] = mapped_column(
        Numeric(6, 2), nullable=True,
    )  # kg
    height: Mapped[float | None] = mapped_column(
        Numeric(5, 1), nullable=True,
    )  # cm
    bmi: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True,
    )  # computed on write
    pain_score: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )  # 0–10

    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now(),
    )

    encounter = relationship("Encounter", back_populates="vitals")


# ──────────────────────────────────────────────────────────────────────
# 3. EncounterNote (SOAP)
# ──────────────────────────────────────────────────────────────────────
class EncounterNote(BaseModel):
    __tablename__ = "encounter_notes"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("encounters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    note_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="SOAP",
    )  # SOAP | PROGRESS | PROCEDURE | DISCHARGE

    subjective: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan: Mapped[str | None] = mapped_column(Text, nullable=True)

    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    author_role: Mapped[str | None] = mapped_column(String(50), nullable=True)

    is_signed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )
    signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1",
    )

    encounter = relationship("Encounter", back_populates="notes")


# ──────────────────────────────────────────────────────────────────────
# 4. EncounterDiagnosis
# ──────────────────────────────────────────────────────────────────────
class EncounterDiagnosis(BaseModel):
    __tablename__ = "encounter_diagnoses"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("encounters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    icd_code: Mapped[str] = mapped_column(String(20), nullable=False)
    icd_description: Mapped[str] = mapped_column(String(500), nullable=False)
    diagnosis_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PRIMARY",
    )  # PRIMARY | SECONDARY | DIFFERENTIAL | RULE_OUT
    onset_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_chronic_condition: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )

    added_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )

    encounter = relationship("Encounter", back_populates="diagnoses")


# ──────────────────────────────────────────────────────────────────────
# 5. EncounterOrder
# ──────────────────────────────────────────────────────────────────────
class EncounterOrder(BaseModel):
    __tablename__ = "encounter_orders"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("encounters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    order_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )  # LAB | IMAGING | MEDICATION | PROCEDURE | REFERRAL
    order_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    order_description: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDING",
    )  # PENDING | SENT | IN_PROGRESS | RESULTED | CANCELLED
    priority: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ROUTINE",
    )  # ROUTINE | URGENT | STAT

    ordered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    ordered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now(),
    )
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    encounter = relationship("Encounter", back_populates="orders")


# ──────────────────────────────────────────────────────────────────────
# 6. EncounterMedication (Prescription)
# ──────────────────────────────────────────────────────────────────────
class EncounterMedication(BaseModel):
    __tablename__ = "encounter_medications"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("encounters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    drug_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    drug_name: Mapped[str] = mapped_column(String(255), nullable=False)
    generic_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dosage: Mapped[str] = mapped_column(String(100), nullable=False)
    dosage_unit: Mapped[str] = mapped_column(String(50), nullable=False)
    frequency: Mapped[str] = mapped_column(String(100), nullable=False)
    route: Mapped[str] = mapped_column(String(50), nullable=False)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    special_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_controlled_substance: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )

    prescribed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    prescribed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now(),
    )

    encounter = relationship("Encounter", back_populates="medications")


# ──────────────────────────────────────────────────────────────────────
# 7. EncounterDisposition
# ──────────────────────────────────────────────────────────────────────
class EncounterDisposition(BaseModel):
    __tablename__ = "encounter_dispositions"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("encounters.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    disposition_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )  # DISCHARGE | ADMIT | REFER_ER | REFER_SPECIALIST | OBSERVATION
    follow_up_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )
    follow_up_in_days: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    discharge_instructions: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    activity_restrictions: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    diet_instructions: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    patient_education_materials: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
    )  # array of document references

    discharged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    discharged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    encounter = relationship("Encounter", back_populates="disposition")
