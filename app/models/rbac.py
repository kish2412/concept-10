"""
app/models/rbac.py
──────────────────
System permission table (global, not clinic-scoped):
  Permission + RolePermission — the default matrix seeded once.

Clinic-scoped custom roles:
  CustomRole + CustomRolePermission + UserCustomRoleAssignment
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey,
    String, Text, UniqueConstraint, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GlobalModel, Base


# ─────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────

class PermissionAction(str, PyEnum):
    CREATE = "create"
    READ   = "read"
    UPDATE = "update"
    DELETE = "delete"


class PermissionResource(str, PyEnum):
    PATIENT         = "patient"
    PATIENT_HISTORY = "patient_history"
    CLINICAL_NOTES  = "clinical_notes"
    CHIEF_COMPLAINT = "chief_complaint"
    VITALS          = "vitals"
    PRESCRIPTION    = "prescription"
    INVESTIGATION   = "investigation"
    NURSING_NOTES   = "nursing_notes"
    QUEUE           = "queue"
    APPOINTMENT     = "appointment"
    CHECKIN         = "checkin"
    USER_MANAGEMENT = "user_management"
    CLINIC_SETTINGS = "clinic_settings"
    REPORTS         = "reports"
    AUDIT_LOGS      = "audit_logs"
    INVOICE         = "invoice"
    PAYMENT         = "payment"
    FEE_TEMPLATE    = "fee_template"

def _enum_values(enum_cls) -> list[str]:
    return [e.value for e in enum_cls]


# ─────────────────────────────────────────────────────────────────────
# System permissions (global — one set for all clinics)
# ─────────────────────────────────────────────────────────────────────

class Permission(GlobalModel):
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("action", "resource", name="uq_permissions_action_resource"),
    )

    action: Mapped[PermissionAction] = mapped_column(
        Enum(PermissionAction, name="permissionaction", values_callable=_enum_values),
        nullable=False,
    )
    resource: Mapped[PermissionResource] = mapped_column(
        Enum(PermissionResource, name="permissionresource", values_callable=_enum_values),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    role_permissions = relationship("RolePermission", back_populates="permission")


class RolePermission(GlobalModel):
    """Maps a system role name → Permission."""
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role", "permission_id", name="uq_role_permissions_role_permission"),
    )

    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    permission = relationship("Permission", back_populates="role_permissions")


# ─────────────────────────────────────────────────────────────────────
# Custom roles (clinic-scoped)
# ─────────────────────────────────────────────────────────────────────

class CustomRole(Base):
    """Admin-defined roles per clinic. Requires clinic.allow_custom_roles = True."""
    __tablename__ = "custom_roles"
    __table_args__ = (
        UniqueConstraint("clinic_id", "slug", name="uq_custom_roles_clinic_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    based_on_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow)

    clinic = relationship("Clinic", back_populates="custom_roles")
    permissions = relationship("CustomRolePermission", back_populates="custom_role", cascade="all, delete-orphan")
    assignments = relationship("UserCustomRoleAssignment", back_populates="custom_role", cascade="all, delete-orphan")


class CustomRolePermission(Base):
    __tablename__ = "custom_role_permissions"
    __table_args__ = (
        UniqueConstraint("custom_role_id", "action", "resource", name="uq_custom_role_permissions"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    custom_role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("custom_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[PermissionAction] = mapped_column(
        Enum(PermissionAction, name="permissionaction", values_callable=_enum_values),
        nullable=False,
    )
    resource: Mapped[PermissionResource] = mapped_column(
        Enum(PermissionResource, name="permissionresource", values_callable=_enum_values),
        nullable=False,
    )
    granted_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")

    custom_role = relationship("CustomRole", back_populates="permissions")


class UserCustomRoleAssignment(Base):
    """A user can hold a system role (users.role) + any number of custom roles."""
    __tablename__ = "user_custom_role_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", "custom_role_id", name="uq_user_custom_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    custom_role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("custom_roles.id", ondelete="CASCADE"), nullable=False
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    assigned_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="custom_role_assignments")
    custom_role = relationship("CustomRole", back_populates="assignments")
