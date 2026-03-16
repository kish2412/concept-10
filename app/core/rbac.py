"""
app/core/rbac.py
────────────────
Clean DB-driven RBAC. No legacy shims.

Usage in route handlers:

    # Simple role guard:
    @router.post("", dependencies=[Depends(require_role(UserRole.ADMIN))])

    # Fine-grained permission guard:
    @router.get("", dependencies=[Depends(require_permission(PermissionAction.READ, PermissionResource.PATIENT))])

    # Rich context (use when you need user/clinic info inside the handler):
    @router.patch("/{id}")
    async def update(id: UUID, ctx: UserContext = Depends(get_user_context)):
        ctx.assert_can(PermissionAction.UPDATE, PermissionResource.PATIENT)
        ...
"""
import logging
from dataclasses import dataclass, field
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.rbac import (
    CustomRole, CustomRolePermission, Permission,
    PermissionAction, PermissionResource,
    RolePermission, UserCustomRoleAssignment,
)
from app.models.user import UserRole

logger = logging.getLogger("app.rbac")


# ─────────────────────────────────────────────────────────────────────
# UserContext — resolved once per request
# ─────────────────────────────────────────────────────────────────────

@dataclass
class UserContext:
    user_id: str
    clinic_id: str
    system_role: UserRole
    permissions: set[tuple[PermissionAction, PermissionResource]]
    custom_roles: list[CustomRole] = field(default_factory=list)

    # ── Checks ────────────────────────────────────────────────────────

    def can(self, action: PermissionAction, resource: PermissionResource) -> bool:
        if self.system_role == UserRole.ADMIN:
            return True
        return (action, resource) in self.permissions

    def has_role(self, *roles: UserRole) -> bool:
        return self.system_role in roles

    def has_custom_role(self, slug: str) -> bool:
        return any(r.slug == slug for r in self.custom_roles)

    # ── Assertions (raise 403 on failure) ────────────────────────────

    def assert_can(self, action: PermissionAction, resource: PermissionResource) -> None:
        if not self.can(action, resource):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {action.value}:{resource.value}",
            )

    def assert_role(self, *roles: UserRole) -> None:
        if not self.has_role(*roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {[r.value for r in roles]}",
            )

    @property
    def clinic_uuid(self) -> UUID:
        return UUID(self.clinic_id)

    @property
    def user_uuid(self) -> UUID:
        return UUID(self.user_id)


# ─────────────────────────────────────────────────────────────────────
# Permission loader
# ─────────────────────────────────────────────────────────────────────

async def _load_permissions(
    system_role: UserRole,
    user_id: str,
    clinic_id: str,
    db: AsyncSession,
) -> tuple[set[tuple], list[CustomRole]]:
    """Load system + custom permissions for this user. One DB round-trip each."""

    # System role permissions
    sys_result = await db.execute(
        select(Permission.action, Permission.resource)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role == system_role.value)
    )
    sys_perms: set[tuple] = {(r[0], r[1]) for r in sys_result.fetchall()}

    # Custom role assignments + permissions
    try:
        uid, cid = UUID(user_id), UUID(clinic_id)
    except ValueError:
        return sys_perms, []

    custom_result = await db.execute(
        select(CustomRole)
        .join(UserCustomRoleAssignment, UserCustomRoleAssignment.custom_role_id == CustomRole.id)
        .where(
            UserCustomRoleAssignment.user_id == uid,
            UserCustomRoleAssignment.clinic_id == cid,
            UserCustomRoleAssignment.is_active.is_(True),
            CustomRole.is_active.is_(True),
        )
    )
    custom_roles = list(custom_result.scalars().all())

    if not custom_roles:
        return sys_perms, []

    perm_result = await db.execute(
        select(CustomRolePermission.action, CustomRolePermission.resource)
        .where(CustomRolePermission.custom_role_id.in_([r.id for r in custom_roles]))
    )
    custom_perms: set[tuple] = {(r[0], r[1]) for r in perm_result.fetchall()}

    return sys_perms | custom_perms, custom_roles


# ─────────────────────────────────────────────────────────────────────
# FastAPI dependencies
# ─────────────────────────────────────────────────────────────────────

async def get_user_context(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserContext:
    """
    Primary dependency for all protected routes.
    Resolves the full UserContext from request.state (set by AuthMiddleware).
    """
    user_id = getattr(request.state, "user_id", None)
    clinic_id = getattr(request.state, "clinic_id", None)
    role_str = getattr(request.state, "user_role", None)

    if not user_id or not clinic_id or not role_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        system_role = UserRole(role_str)
    except ValueError:
        system_role = UserRole.RECEPTIONIST

    permissions, custom_roles = await _load_permissions(system_role, user_id, clinic_id, db)

    return UserContext(
        user_id=user_id,
        clinic_id=clinic_id,
        system_role=system_role,
        permissions=permissions,
        custom_roles=custom_roles,
    )


def require_permission(action: PermissionAction, resource: PermissionResource):
    """Route dependency: raises 403 if user lacks the permission."""
    async def _guard(ctx: UserContext = Depends(get_user_context)) -> UserContext:
        ctx.assert_can(action, resource)
        return ctx
    return _guard


def require_role(*roles: UserRole):
    """Route dependency: raises 403 if user's system role is not in the list."""
    async def _guard(ctx: UserContext = Depends(get_user_context)) -> UserContext:
        ctx.assert_role(*roles)
        return ctx
    return _guard


def require_admin():
    """Shorthand for require_role(UserRole.ADMIN)."""
    return require_role(UserRole.ADMIN)
