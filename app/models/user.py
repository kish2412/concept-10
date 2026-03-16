"""app/models/user.py"""
import uuid
from enum import Enum as PyEnum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantModel


class UserRole(str, PyEnum):
    ADMIN        = "admin"
    RECEPTIONIST = "receptionist"
    NURSE        = "nurse"
    DOCTOR       = "doctor"
    CONSULTANT   = "consultant"
    BILLING      = "billing"

def _enum_values(enum_cls) -> list[str]:
    return [e.value for e in enum_cls]


class User(TenantModel):
    __tablename__ = "users"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Clerk link ─────────────────────────────────────────────────────
    # Populated via Clerk webhook when user signs up.
    # Null for users created via local /auth/login (dev/admin bootstrap).
    clerk_user_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True, index=True
    )

    # ── Profile ────────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    specialisation: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── Auth ───────────────────────────────────────────────────────────
    # Empty string for Clerk-only users (they never use password login).
    # Populated only for dev/admin users created directly.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    # ── Role ───────────────────────────────────────────────────────────
    # Primary system role. Custom roles are in user_custom_role_assignments.
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole", values_callable=_enum_values),
        nullable=False,
        default=UserRole.RECEPTIONIST,
        server_default=UserRole.RECEPTIONIST.value,
    )

    # ── Relationships ──────────────────────────────────────────────────
    clinic = relationship("Clinic", back_populates="users", lazy="joined")
    custom_role_assignments = relationship(
        "UserCustomRoleAssignment",
        back_populates="user",
        cascade="all, delete-orphan",
    )
