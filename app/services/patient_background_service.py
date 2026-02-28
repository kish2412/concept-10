import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient_background import PatientBackground
from app.schemas.patient_background import PatientBackgroundUpdate
from app.services.patient_service import get_patient_by_id


async def get_patient_background(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
) -> PatientBackground | None:
    result = await db.execute(
        select(PatientBackground).where(
            PatientBackground.patient_id == patient_id,
            PatientBackground.clinic_id == clinic_id,
            PatientBackground.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()


async def get_or_create_patient_background(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
) -> PatientBackground | None:
    patient = await get_patient_by_id(db=db, clinic_id=clinic_id, patient_id=patient_id)
    if not patient:
        return None

    background = await get_patient_background(db=db, clinic_id=clinic_id, patient_id=patient_id)
    if background:
        return background

    background = PatientBackground(clinic_id=clinic_id, patient_id=patient_id)
    db.add(background)
    await db.commit()
    await db.refresh(background)
    return background


async def update_patient_background(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    payload: PatientBackgroundUpdate,
) -> PatientBackground | None:
    background = await get_or_create_patient_background(db=db, clinic_id=clinic_id, patient_id=patient_id)
    if not background:
        return None

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(background, field, value)

    await db.commit()
    await db.refresh(background)
    return background