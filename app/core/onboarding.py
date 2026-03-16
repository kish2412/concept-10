import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import Clinic

PENDING_CLINIC_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


async def ensure_pending_clinic(session: AsyncSession) -> Clinic:
    result = await session.execute(select(Clinic).where(Clinic.id == PENDING_CLINIC_ID))
    clinic = result.scalar_one_or_none()
    if clinic:
        return clinic

    await session.execute(
        insert(Clinic)
        .values(
            id=PENDING_CLINIC_ID,
            clinic_id=PENDING_CLINIC_ID,
            name="Pending Onboarding",
            is_active=False,
            is_deleted=True,
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )

    result = await session.execute(select(Clinic).where(Clinic.id == PENDING_CLINIC_ID))
    clinic = result.scalar_one()
    return clinic