"""
app/api/v1/routes/tenants.py
──────────────────────────────
Clinic (tenant) management. Replaces the auto-create logic that was in middleware.
"""
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import UserContext, get_user_context, require_role
from app.models.clinic import Clinic
from app.models.user import User, UserRole
from app.seeds.rbac_seed import seed_visit_flow_for_clinic

router = APIRouter()


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# ── Schemas ───────────────────────────────────────────────────────────

class ClinicCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str | None = None


class ClinicUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    allow_custom_roles: bool | None = None
    max_custom_roles: int | None = Field(None, ge=0)
    ai_enabled: bool | None = None


# ── Routes ────────────────────────────────────────────────────────────

@router.get("/mine")
async def my_tenants(
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return clinics the current user belongs to."""
    result = await db.execute(
        select(Clinic).where(
            Clinic.id == ctx.clinic_uuid,
            Clinic.is_deleted.is_(False),
        )
    )
    clinics = result.scalars().all()
    return [{"id": str(c.id), "name": c.name, "slug": c.slug} for c in clinics]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_clinic(
    payload: ClinicCreate,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Create a new clinic and assign the requesting user as admin.
    Called after a new user signs up and chooses "Create a new clinic".
    """
    slug = payload.slug or _slugify(payload.name)

    # Check slug uniqueness
    exists = await db.execute(select(Clinic.id).where(Clinic.slug == slug))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Slug '{slug}' already taken")

    clinic = Clinic(
        clinic_id=uuid.uuid4(),  # self-referencing (TenantModel requirement)
        name=payload.name,
        slug=slug,
    )
    db.add(clinic)
    await db.flush()

    # Update the requesting user's clinic assignment and role
    user = await db.get(User, ctx.user_uuid)
    if user:
        user.clinic_id = clinic.id
        user.role = UserRole.ADMIN

    await db.flush()

    # Seed default visit flow for this clinic
    await seed_visit_flow_for_clinic(clinic.id, db)

    await db.commit()

    return {"id": str(clinic.id), "name": clinic.name, "slug": clinic.slug}


@router.get("/me")
async def current_clinic(
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    clinic = await db.get(Clinic, ctx.clinic_uuid)
    if not clinic or clinic.is_deleted:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return {
        "id": str(clinic.id),
        "name": clinic.name,
        "slug": clinic.slug,
        "allow_custom_roles": clinic.allow_custom_roles,
        "max_custom_roles": clinic.max_custom_roles,
        "ai_enabled": clinic.ai_enabled,
    }


@router.patch("/me", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def update_clinic(
    payload: ClinicUpdate,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    clinic = await db.get(Clinic, ctx.clinic_uuid)
    if not clinic or clinic.is_deleted:
        raise HTTPException(status_code=404, detail="Clinic not found")

    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(clinic, field, val)

    await db.commit()
    return {"ok": True}
