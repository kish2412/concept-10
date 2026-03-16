"""
app/api/v1/routes/roles.py
──────────────────────────
Custom role management. Admin-only.
"""
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import UserContext, get_user_context, require_role
from app.models.clinic import Clinic
from app.models.rbac import (
    CustomRole, CustomRolePermission, UserCustomRoleAssignment,
    PermissionAction, PermissionResource,
)
from app.models.user import UserRole

router = APIRouter()


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


# ── Schemas ───────────────────────────────────────────────────────────

class PermissionItem(BaseModel):
    action: PermissionAction
    resource: PermissionResource


class CustomRoleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = None
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    based_on_role: str | None = None
    permissions: list[PermissionItem] = []


class CustomRolePermissionsUpdate(BaseModel):
    permissions: list[PermissionItem]


class RoleAssignRequest(BaseModel):
    user_id: uuid.UUID


# ── Routes ────────────────────────────────────────────────────────────

@router.get("", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def list_custom_roles(
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(CustomRole).where(
            CustomRole.clinic_id == ctx.clinic_uuid,
            CustomRole.is_active.is_(True),
        )
    )
    roles = result.scalars().all()
    return [{"id": str(r.id), "name": r.name, "slug": r.slug, "color": r.color} for r in roles]


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(UserRole.ADMIN))])
async def create_custom_role(
    payload: CustomRoleCreate,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    clinic = await db.get(Clinic, ctx.clinic_uuid)
    if not clinic or not clinic.allow_custom_roles:
        raise HTTPException(status_code=403, detail="Custom roles not enabled for this clinic")

    # Enforce cap
    count = await db.scalar(
        select(func.count(CustomRole.id)).where(
            CustomRole.clinic_id == ctx.clinic_uuid,
            CustomRole.is_active.is_(True),
        )
    )
    if clinic.max_custom_roles > 0 and (count or 0) >= clinic.max_custom_roles:
        raise HTTPException(status_code=422, detail=f"Custom role limit ({clinic.max_custom_roles}) reached")

    # Anti-escalation: can only grant what you yourself have
    for p in payload.permissions:
        if (p.action, p.resource) not in ctx.permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Cannot grant permission you don't hold: {p.action.value}:{p.resource.value}",
            )

    slug = _slugify(payload.name)
    existing = await db.scalar(
        select(CustomRole.id).where(CustomRole.clinic_id == ctx.clinic_uuid, CustomRole.slug == slug)
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Role with slug '{slug}' already exists")

    role = CustomRole(
        clinic_id=ctx.clinic_uuid,
        name=payload.name,
        slug=slug,
        description=payload.description,
        color=payload.color,
        based_on_role=payload.based_on_role,
        created_by=ctx.user_id,
    )
    db.add(role)
    await db.flush()

    for p in payload.permissions:
        db.add(CustomRolePermission(
            custom_role_id=role.id,
            action=p.action,
            resource=p.resource,
            granted_by=ctx.user_id,
        ))

    await db.commit()
    return {"id": str(role.id), "name": role.name, "slug": role.slug}


@router.put("/{role_id}/permissions", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def update_role_permissions(
    role_id: uuid.UUID,
    payload: CustomRolePermissionsUpdate,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    role = await db.scalar(
        select(CustomRole).where(CustomRole.id == role_id, CustomRole.clinic_id == ctx.clinic_uuid)
    )
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    for p in payload.permissions:
        if (p.action, p.resource) not in ctx.permissions:
            raise HTTPException(status_code=403, detail=f"Cannot grant: {p.action.value}:{p.resource.value}")

    # Replace all permissions
    existing = await db.execute(select(CustomRolePermission).where(CustomRolePermission.custom_role_id == role_id))
    for perm in existing.scalars().all():
        await db.delete(perm)

    for p in payload.permissions:
        db.add(CustomRolePermission(custom_role_id=role_id, action=p.action, resource=p.resource, granted_by=ctx.user_id))

    await db.commit()
    return {"ok": True}


@router.post("/{role_id}/assign", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def assign_role(
    role_id: uuid.UUID,
    payload: RoleAssignRequest,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    role = await db.scalar(
        select(CustomRole).where(CustomRole.id == role_id, CustomRole.clinic_id == ctx.clinic_uuid, CustomRole.is_active.is_(True))
    )
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    existing = await db.scalar(
        select(UserCustomRoleAssignment.id).where(
            UserCustomRoleAssignment.user_id == payload.user_id,
            UserCustomRoleAssignment.custom_role_id == role_id,
            UserCustomRoleAssignment.is_active.is_(True),
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Role already assigned")

    db.add(UserCustomRoleAssignment(
        user_id=payload.user_id,
        custom_role_id=role_id,
        clinic_id=ctx.clinic_uuid,
        assigned_by=ctx.user_id,
    ))
    await db.commit()
    return {"ok": True}


@router.delete("/{role_id}", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def deactivate_role(
    role_id: uuid.UUID,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    role = await db.scalar(
        select(CustomRole).where(CustomRole.id == role_id, CustomRole.clinic_id == ctx.clinic_uuid)
    )
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    role.is_active = False
    assignments = await db.execute(
        select(UserCustomRoleAssignment).where(
            UserCustomRoleAssignment.custom_role_id == role_id,
            UserCustomRoleAssignment.is_active.is_(True),
        )
    )
    from datetime import datetime
    for a in assignments.scalars().all():
        a.is_active = False
        a.revoked_at = datetime.utcnow()

    await db.commit()
    return {"ok": True}
