import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, get_current_user_id
from app.core.database import get_db
from app.core.rbac import authorize_role
from app.models.clinic import Clinic
from app.schemas.clinic import ClinicAISettingsResponse, ClinicAISettingsUpdate

router = APIRouter()


@router.get("/me")
async def clinic_context(
    clinic_id: str = Depends(get_current_tenant_id),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    return {"clinic_id": clinic_id, "user_id": user_id}


def _parse_clinic_uuid(clinic_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(clinic_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tenant context",
        ) from exc


@router.get(
    "/me/ai-settings",
    response_model=ClinicAISettingsResponse,
    dependencies=[Depends(authorize_role("admin", "provider", "nurse", "viewer"))],
    summary="Get AI feature settings for the current clinic",
)
async def get_ai_settings(
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ClinicAISettingsResponse:
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    result = await db.execute(
        select(Clinic).where(
            Clinic.id == clinic_uuid,
            Clinic.is_deleted.is_(False),
        )
    )
    clinic = result.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")

    return ClinicAISettingsResponse(
        ai_enabled=clinic.ai_enabled,
        ai_policy_tier=clinic.ai_policy_tier,
        ai_guardrail_profile=clinic.ai_guardrail_profile,
    )


@router.patch(
    "/me/ai-settings",
    response_model=ClinicAISettingsResponse,
    dependencies=[Depends(authorize_role("admin"))],
    summary="Update AI feature settings for the current clinic (admin only)",
)
async def update_ai_settings(
    payload: ClinicAISettingsUpdate,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ClinicAISettingsResponse:
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    result = await db.execute(
        select(Clinic).where(
            Clinic.id == clinic_uuid,
            Clinic.is_deleted.is_(False),
        )
    )
    clinic = result.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(clinic, field, value)

    await db.commit()
    await db.refresh(clinic)

    return ClinicAISettingsResponse(
        ai_enabled=clinic.ai_enabled,
        ai_policy_tier=clinic.ai_policy_tier,
        ai_guardrail_profile=clinic.ai_guardrail_profile,
    )
