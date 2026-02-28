import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate


async def list_patients(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    page: int,
    size: int,
    search: str | None = None,
) -> tuple[list[Patient], int]:
    filters = [Patient.clinic_id == clinic_id, Patient.is_deleted.is_(False)]

    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Patient.first_name.ilike(term),
                Patient.last_name.ilike(term),
                func.concat(Patient.first_name, " ", Patient.last_name).ilike(term),
                Patient.phone.ilike(term),
            )
        )

    where_clause = and_(*filters)
    offset = (page - 1) * size

    total_result = await db.execute(select(func.count()).select_from(Patient).where(where_clause))
    total = total_result.scalar_one()

    result = await db.execute(
        select(Patient)
        .where(where_clause)
        .order_by(Patient.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    return list(result.scalars().all()), total


async def get_patient_by_id(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> Patient | None:
    result = await db.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.clinic_id == clinic_id,
            Patient.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()


async def create_patient(db: AsyncSession, clinic_id: uuid.UUID, payload: PatientCreate) -> Patient:
    patient = Patient(clinic_id=clinic_id, **payload.model_dump())
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


async def update_patient(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    payload: PatientUpdate,
) -> Patient | None:
    patient = await get_patient_by_id(db=db, clinic_id=clinic_id, patient_id=patient_id)
    if not patient:
        return None

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(patient, field, value)

    await db.commit()
    await db.refresh(patient)
    return patient


async def soft_delete_patient(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> bool:
    patient = await get_patient_by_id(db=db, clinic_id=clinic_id, patient_id=patient_id)
    if not patient:
        return False

    patient.is_deleted = True
    patient.is_active = False
    await db.commit()
    return True
