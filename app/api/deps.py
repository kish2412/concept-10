import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.clinic import Clinic


def get_current_tenant_id(request: Request) -> str:
    clinic_id = getattr(request.state, "clinic_id", None)
    if not clinic_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing tenant context")
    return clinic_id


def get_current_user_id(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing user context")
    return user_id


async def validate_encounter_exists(
    id: uuid.UUID,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    """Verify encounter exists and belongs to the tenant before sub-resource ops."""
    from app.services.encounter_service import get_encounter_by_id

    clinic_uuid = uuid.UUID(clinic_id)
    encounter = await get_encounter_by_id(db=db, clinic_id=clinic_uuid, encounter_id=id)
    if not encounter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")
    return id


TenantIdDep = Depends(get_current_tenant_id)
UserIdDep = Depends(get_current_user_id)


async def require_ai_feature_enabled(
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> Clinic:
    if not settings.agentic_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI workflows are disabled by system configuration",
        )

    try:
        clinic_uuid = uuid.UUID(clinic_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant context") from exc

    result = await db.execute(
        select(Clinic).where(
            Clinic.id == clinic_uuid,
            Clinic.is_deleted.is_(False),
        )
    )
    clinic = result.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if not clinic.ai_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI features are not enabled for this clinic",
        )
    return clinic
