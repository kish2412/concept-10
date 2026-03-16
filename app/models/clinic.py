"""app/models/clinic.py"""
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantModel


class Clinic(TenantModel):
    __tablename__ = "clinics"

    # ── Identity ──────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True, index=True)

    # Clerk org ID stored here during transition; nullable after full migration
    external_org_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # ── AI settings ────────────────────────────────────────────────────
    ai_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    ai_policy_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_guardrail_profile: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── RBAC feature flags ─────────────────────────────────────────────
    # Platform admin flips this to True to unlock custom role management for a clinic.
    allow_custom_roles: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    # 0 = unlimited (enterprise). Default 5.
    max_custom_roles: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default="5"
    )

    # ── Relationships ──────────────────────────────────────────────────
    users = relationship("User", back_populates="clinic", lazy="selectin")
    custom_roles = relationship(
        "CustomRole", back_populates="clinic", cascade="all, delete-orphan"
    )
    visit_flow_config = relationship(
        "VisitFlowConfig", back_populates="clinic", uselist=False
    )
