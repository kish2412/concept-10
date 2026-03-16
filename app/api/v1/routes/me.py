"""
app/api/v1/routes/me.py
────────────────────────
/me/permissions  — called by frontend on load to populate PermissionContext
/me/profile      — current user profile
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import UserContext, get_user_context
from app.models.clinic import Clinic
from app.models.user import User

router = APIRouter()


@router.get("/permissions")
async def my_permissions(
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns full permission set + clinic info for the current user.
    Frontend PermissionProvider calls this on every app load.
    """
    clinic = await db.get(Clinic, ctx.clinic_uuid)
    if not clinic or clinic.is_deleted:
        raise HTTPException(status_code=404, detail="Clinic not found")

    return {
        "user_id":     ctx.user_id,
        "clinic_id":   ctx.clinic_id,
        "clinic_name": clinic.name,
        "clinic_slug": clinic.slug,
        "system_role": ctx.system_role.value,
        "custom_roles": [
            {"id": str(r.id), "name": r.name, "slug": r.slug, "color": r.color}
            for r in ctx.custom_roles
        ],
        "permissions": [
            {"action": a.value, "resource": r.value}
            for a, r in ctx.permissions
        ],
        "features": {
            "allow_custom_roles": clinic.allow_custom_roles,
            "ai_enabled":         clinic.ai_enabled,
        },
    }


@router.get("/profile")
async def my_profile(
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await db.get(User, ctx.user_uuid)
    if not user or user.is_deleted:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id":            str(user.id),
        "email":         user.email,
        "full_name":     user.full_name,
        "role":          user.role.value,
        "department":    user.department,
        "specialisation": user.specialisation,
    }


@router.patch("/profile")
async def update_my_profile(
    payload: dict,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await db.get(User, ctx.user_uuid)
    if not user or user.is_deleted:
        raise HTTPException(status_code=404, detail="User not found")

    allowed = {"full_name", "phone", "department", "specialisation"}
    for field, val in payload.items():
        if field in allowed:
            setattr(user, field, val)

    await db.commit()
    return {"ok": True}
