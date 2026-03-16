"""
app/models/visit_flow.py
─────────────────────────
Clinic-configurable visit state machine.
VisitStatus strings intentionally match your existing Encounter.status values
so the encounter queue keeps working without changes.
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class VisitStatus(str, PyEnum):
    # Maps to existing Encounter.status values
    REGISTERED            = "REGISTERED"
    CHECKED_IN            = "CHECKED_IN"
    IN_QUEUE              = "IN_QUEUE"
    WITH_NURSE            = "TRIAGE"            # existing value in your DB
    WAITING_FOR_DOCTOR    = "WAITING_FOR_DOCTOR"
    WITH_DOCTOR           = "WITH_PROVIDER"     # existing value
    INVESTIGATION_PENDING = "PENDING_RESULTS"   # existing value
    PRESCRIPTION_ISSUED   = "PENDING_REVIEW"    # existing value
    BILLING               = "BILLING"
    COMPLETED             = "DISCHARGED"        # existing value
    CANCELLED             = "CANCELLED"
    NO_SHOW               = "NO_SHOW"


MANDATORY_STATES = frozenset({
    VisitStatus.REGISTERED,
    VisitStatus.CHECKED_IN,
    VisitStatus.WITH_DOCTOR,
    VisitStatus.COMPLETED,
})

OPTIONAL_STATES = frozenset({
    VisitStatus.IN_QUEUE,
    VisitStatus.WITH_NURSE,
    VisitStatus.WAITING_FOR_DOCTOR,
    VisitStatus.INVESTIGATION_PENDING,
    VisitStatus.PRESCRIPTION_ISSUED,
    VisitStatus.BILLING,
})

DEFAULT_STATE_ORDER: dict[VisitStatus, int] = {
    VisitStatus.REGISTERED:             10,
    VisitStatus.CHECKED_IN:             20,
    VisitStatus.IN_QUEUE:               30,
    VisitStatus.WITH_NURSE:             40,
    VisitStatus.WAITING_FOR_DOCTOR:     50,
    VisitStatus.WITH_DOCTOR:            60,
    VisitStatus.INVESTIGATION_PENDING:  70,
    VisitStatus.PRESCRIPTION_ISSUED:    80,
    VisitStatus.BILLING:                90,
    VisitStatus.COMPLETED:              100,
    VisitStatus.CANCELLED:              999,
    VisitStatus.NO_SHOW:                998,
}

DEFAULT_TRANSITION_ROLES: dict[tuple[VisitStatus, VisitStatus], list[str]] = {
    (VisitStatus.REGISTERED,             VisitStatus.CHECKED_IN):            ["receptionist", "admin"],
    (VisitStatus.CHECKED_IN,             VisitStatus.IN_QUEUE):              ["receptionist", "admin"],
    (VisitStatus.IN_QUEUE,               VisitStatus.WITH_NURSE):            ["nurse", "admin"],
    (VisitStatus.IN_QUEUE,               VisitStatus.WITH_DOCTOR):           ["doctor", "consultant", "admin"],
    (VisitStatus.WITH_NURSE,             VisitStatus.WAITING_FOR_DOCTOR):    ["nurse", "admin"],
    (VisitStatus.WAITING_FOR_DOCTOR,     VisitStatus.WITH_DOCTOR):           ["doctor", "consultant", "admin"],
    (VisitStatus.WITH_DOCTOR,            VisitStatus.INVESTIGATION_PENDING): ["doctor", "consultant"],
    (VisitStatus.INVESTIGATION_PENDING,  VisitStatus.WITH_DOCTOR):           ["doctor", "consultant", "nurse"],
    (VisitStatus.WITH_DOCTOR,            VisitStatus.PRESCRIPTION_ISSUED):   ["doctor", "consultant"],
    (VisitStatus.WITH_DOCTOR,            VisitStatus.BILLING):               ["doctor", "consultant"],
    (VisitStatus.PRESCRIPTION_ISSUED,    VisitStatus.BILLING):               ["billing", "receptionist", "admin"],
    (VisitStatus.PRESCRIPTION_ISSUED,    VisitStatus.COMPLETED):             ["doctor", "admin"],
    (VisitStatus.BILLING,                VisitStatus.COMPLETED):             ["billing", "receptionist", "admin"],
    (VisitStatus.REGISTERED,             VisitStatus.CANCELLED):             ["receptionist", "admin"],
    (VisitStatus.CHECKED_IN,             VisitStatus.CANCELLED):             ["receptionist", "admin"],
    (VisitStatus.IN_QUEUE,               VisitStatus.CANCELLED):             ["receptionist", "admin", "nurse"],
    (VisitStatus.CHECKED_IN,             VisitStatus.NO_SHOW):               ["receptionist", "admin"],
    (VisitStatus.IN_QUEUE,               VisitStatus.NO_SHOW):               ["receptionist", "admin"],
}


class VisitFlowConfig(Base):
    """One per clinic. Controls the entire visit state machine for that clinic."""
    __tablename__ = "visit_flow_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )
    flow_name: Mapped[str] = mapped_column(String(100), nullable=False, default="Standard OPD Flow", server_default="Standard OPD Flow")
    billing_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    direct_to_doctor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    auto_assign_nurse: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    last_modified_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow)

    clinic = relationship("Clinic", back_populates="visit_flow_config")
    states = relationship("VisitStateConfig", back_populates="flow_config",
                          order_by="VisitStateConfig.order_index", cascade="all, delete-orphan")
    transitions = relationship("VisitTransitionRule", back_populates="flow_config",
                               cascade="all, delete-orphan")


class VisitStateConfig(Base):
    __tablename__ = "visit_state_configs"
    __table_args__ = (UniqueConstraint("flow_config_id", "state", name="uq_visit_state_configs_flow_state"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_config_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("visit_flow_configs.id", ondelete="CASCADE"), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(60), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    display_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    sla_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    flow_config = relationship("VisitFlowConfig", back_populates="states")


class VisitTransitionRule(Base):
    __tablename__ = "visit_transition_rules"
    __table_args__ = (UniqueConstraint("flow_config_id", "from_state", "to_state", name="uq_visit_transition_rules"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_config_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("visit_flow_configs.id", ondelete="CASCADE"), nullable=False, index=True)
    from_state: Mapped[str] = mapped_column(String(60), nullable=False)
    to_state: Mapped[str] = mapped_column(String(60), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    allowed_roles: Mapped[list] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    is_bypass: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    requires_note: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow)

    flow_config = relationship("VisitFlowConfig", back_populates="transitions")
