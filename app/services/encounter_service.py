import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.encounter import (
    Encounter,
    EncounterDiagnosis,
    EncounterDisposition,
    EncounterMedication,
    EncounterNote,
    EncounterOrder,
    EncounterVitals,
)
from app.schemas.encounter import (
    DiagnosisCreate,
    DiagnosisUpdate,
    DispositionCreate,
    DispositionUpdate,
    EncounterCreate,
    EncounterUpdate,
    MedicationCreate,
    MedicationUpdate,
    NoteCreate,
    NoteUpdate,
    OrderCreate,
    OrderUpdate,
    StatusUpdate,
    VitalsCreate,
    VitalsUpdate,
)


class EncounterStatusTransitionError(ValueError):
    """Raised when an encounter status transition violates workflow requirements."""


# ═════════════════════════════════════════════════════════════════════
#  Helpers
# ═════════════════════════════════════════════════════════════════════

def _generate_encounter_id() -> str:
    """Generate human-readable encounter id: ENC-YYYYMMDD-XXXX."""
    now = datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d")
    random_part = uuid.uuid4().hex[:4].upper()
    return f"ENC-{date_part}-{random_part}"


def _compute_bmi(weight: float | None, height: float | None) -> float | None:
    """BMI = weight(kg) / (height(m))^2."""
    if weight and height and height > 0:
        height_m = height / 100.0
        return round(weight / (height_m * height_m), 2)
    return None


# ═════════════════════════════════════════════════════════════════════
#  1. Encounter CRUD
# ═════════════════════════════════════════════════════════════════════

async def list_encounters(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    page: int,
    size: int,
    search: str | None = None,
    status: str | None = None,
    encounter_type: str | None = None,
    patient_id: uuid.UUID | None = None,
    provider_id: uuid.UUID | None = None,
) -> tuple[list[Encounter], int]:
    filters = [
        Encounter.clinic_id == clinic_id,
        Encounter.is_deleted.is_(False),
        Encounter.deleted_at.is_(None),
    ]

    if patient_id:
        filters.append(Encounter.patient_id == patient_id)
    if provider_id:
        filters.append(Encounter.provider_id == provider_id)
    if status:
        filters.append(Encounter.status == status)
    if encounter_type:
        filters.append(Encounter.encounter_type == encounter_type)
    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Encounter.chief_complaint.ilike(term),
                Encounter.encounter_id.ilike(term),
            )
        )

    where_clause = and_(*filters)
    offset = (page - 1) * size

    total_result = await db.execute(
        select(func.count()).select_from(Encounter).where(where_clause)
    )
    total = total_result.scalar_one()

    result = await db.execute(
        select(Encounter)
        .where(where_clause)
        .order_by(Encounter.scheduled_at.desc().nullslast(), Encounter.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    return list(result.scalars().all()), total


async def get_encounter_by_id(
    db: AsyncSession, clinic_id: uuid.UUID, encounter_id: uuid.UUID,
) -> Encounter | None:
    result = await db.execute(
        select(Encounter).where(
            Encounter.id == encounter_id,
            Encounter.clinic_id == clinic_id,
            Encounter.is_deleted.is_(False),
            Encounter.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def create_encounter(
    db: AsyncSession, clinic_id: uuid.UUID, payload: EncounterCreate,
) -> Encounter:
    data = payload.model_dump()
    data["encounter_id"] = _generate_encounter_id()
    encounter = Encounter(clinic_id=clinic_id, **data)
    db.add(encounter)
    await db.commit()
    await db.refresh(encounter)
    return encounter


async def update_encounter(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    encounter_id: uuid.UUID,
    payload: EncounterUpdate,
) -> Encounter | None:
    encounter = await get_encounter_by_id(db=db, clinic_id=clinic_id, encounter_id=encounter_id)
    if not encounter:
        return None

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(encounter, field, value)

    await db.commit()
    await db.refresh(encounter)
    return encounter


async def soft_delete_encounter(
    db: AsyncSession, clinic_id: uuid.UUID, encounter_id: uuid.UUID,
) -> bool:
    encounter = await get_encounter_by_id(db=db, clinic_id=clinic_id, encounter_id=encounter_id)
    if not encounter:
        return False
    encounter.is_deleted = True
    encounter.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return True


# ═════════════════════════════════════════════════════════════════════
#  2. Vitals CRUD
# ═════════════════════════════════════════════════════════════════════

async def create_vitals(
    db: AsyncSession, clinic_id: uuid.UUID, encounter_pk: uuid.UUID, payload: VitalsCreate,
) -> EncounterVitals:
    data = payload.model_dump()
    data["bmi"] = _compute_bmi(data.get("weight"), data.get("height"))
    vitals = EncounterVitals(clinic_id=clinic_id, encounter_id=encounter_pk, **data)
    db.add(vitals)
    await db.commit()
    await db.refresh(vitals)
    return vitals


async def update_vitals(
    db: AsyncSession, clinic_id: uuid.UUID, vitals_id: uuid.UUID, payload: VitalsUpdate,
) -> EncounterVitals | None:
    result = await db.execute(
        select(EncounterVitals).where(
            EncounterVitals.id == vitals_id,
            EncounterVitals.clinic_id == clinic_id,
            EncounterVitals.is_deleted.is_(False),
        )
    )
    vitals = result.scalar_one_or_none()
    if not vitals:
        return None

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(vitals, field, value)

    # Recompute BMI
    w = updates.get("weight", vitals.weight)
    h = updates.get("height", vitals.height)
    vitals.bmi = _compute_bmi(w, h)

    await db.commit()
    await db.refresh(vitals)
    return vitals


async def delete_vitals(
    db: AsyncSession, clinic_id: uuid.UUID, vitals_id: uuid.UUID,
) -> bool:
    result = await db.execute(
        select(EncounterVitals).where(
            EncounterVitals.id == vitals_id,
            EncounterVitals.clinic_id == clinic_id,
        )
    )
    vitals = result.scalar_one_or_none()
    if not vitals:
        return False
    vitals.is_deleted = True
    await db.commit()
    return True


# ═════════════════════════════════════════════════════════════════════
#  3. Notes CRUD
# ═════════════════════════════════════════════════════════════════════

async def create_note(
    db: AsyncSession, clinic_id: uuid.UUID, encounter_pk: uuid.UUID, payload: NoteCreate,
) -> EncounterNote:
    note = EncounterNote(clinic_id=clinic_id, encounter_id=encounter_pk, **payload.model_dump())
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


async def update_note(
    db: AsyncSession, clinic_id: uuid.UUID, note_id: uuid.UUID, payload: NoteUpdate,
) -> EncounterNote | None:
    result = await db.execute(
        select(EncounterNote).where(
            EncounterNote.id == note_id,
            EncounterNote.clinic_id == clinic_id,
            EncounterNote.is_deleted.is_(False),
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        return None

    updates = payload.model_dump(exclude_unset=True)

    # Bump version on content changes
    content_fields = {"subjective", "objective", "assessment", "plan"}
    if content_fields & updates.keys():
        note.version = (note.version or 1) + 1

    for field, value in updates.items():
        setattr(note, field, value)

    await db.commit()
    await db.refresh(note)
    return note


async def delete_note(
    db: AsyncSession, clinic_id: uuid.UUID, note_id: uuid.UUID,
) -> bool:
    result = await db.execute(
        select(EncounterNote).where(
            EncounterNote.id == note_id,
            EncounterNote.clinic_id == clinic_id,
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        return False
    note.is_deleted = True
    await db.commit()
    return True


# ═════════════════════════════════════════════════════════════════════
#  4. Diagnosis CRUD
# ═════════════════════════════════════════════════════════════════════

async def create_diagnosis(
    db: AsyncSession, clinic_id: uuid.UUID, encounter_pk: uuid.UUID, payload: DiagnosisCreate,
) -> EncounterDiagnosis:
    dx = EncounterDiagnosis(clinic_id=clinic_id, encounter_id=encounter_pk, **payload.model_dump())
    db.add(dx)
    await db.commit()
    await db.refresh(dx)
    return dx


async def update_diagnosis(
    db: AsyncSession, clinic_id: uuid.UUID, dx_id: uuid.UUID, payload: DiagnosisUpdate,
) -> EncounterDiagnosis | None:
    result = await db.execute(
        select(EncounterDiagnosis).where(
            EncounterDiagnosis.id == dx_id,
            EncounterDiagnosis.clinic_id == clinic_id,
            EncounterDiagnosis.is_deleted.is_(False),
        )
    )
    dx = result.scalar_one_or_none()
    if not dx:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(dx, field, value)
    await db.commit()
    await db.refresh(dx)
    return dx


async def delete_diagnosis(
    db: AsyncSession, clinic_id: uuid.UUID, dx_id: uuid.UUID,
) -> bool:
    result = await db.execute(
        select(EncounterDiagnosis).where(
            EncounterDiagnosis.id == dx_id,
            EncounterDiagnosis.clinic_id == clinic_id,
        )
    )
    dx = result.scalar_one_or_none()
    if not dx:
        return False
    dx.is_deleted = True
    await db.commit()
    return True


# ═════════════════════════════════════════════════════════════════════
#  5. Order CRUD
# ═════════════════════════════════════════════════════════════════════

async def create_order(
    db: AsyncSession, clinic_id: uuid.UUID, encounter_pk: uuid.UUID, payload: OrderCreate,
) -> EncounterOrder:
    order = EncounterOrder(clinic_id=clinic_id, encounter_id=encounter_pk, **payload.model_dump())
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


async def update_order(
    db: AsyncSession, clinic_id: uuid.UUID, order_id: uuid.UUID, payload: OrderUpdate,
) -> EncounterOrder | None:
    result = await db.execute(
        select(EncounterOrder).where(
            EncounterOrder.id == order_id,
            EncounterOrder.clinic_id == clinic_id,
            EncounterOrder.is_deleted.is_(False),
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(order, field, value)
    await db.commit()
    await db.refresh(order)
    return order


async def delete_order(
    db: AsyncSession, clinic_id: uuid.UUID, order_id: uuid.UUID,
) -> bool:
    result = await db.execute(
        select(EncounterOrder).where(
            EncounterOrder.id == order_id,
            EncounterOrder.clinic_id == clinic_id,
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        return False
    order.is_deleted = True
    await db.commit()
    return True


# ═════════════════════════════════════════════════════════════════════
#  6. Medication CRUD
# ═════════════════════════════════════════════════════════════════════

async def create_medication(
    db: AsyncSession, clinic_id: uuid.UUID, encounter_pk: uuid.UUID, payload: MedicationCreate,
) -> EncounterMedication:
    med = EncounterMedication(clinic_id=clinic_id, encounter_id=encounter_pk, **payload.model_dump())
    db.add(med)
    await db.commit()
    await db.refresh(med)
    return med


async def update_medication(
    db: AsyncSession, clinic_id: uuid.UUID, med_id: uuid.UUID, payload: MedicationUpdate,
) -> EncounterMedication | None:
    result = await db.execute(
        select(EncounterMedication).where(
            EncounterMedication.id == med_id,
            EncounterMedication.clinic_id == clinic_id,
            EncounterMedication.is_deleted.is_(False),
        )
    )
    med = result.scalar_one_or_none()
    if not med:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(med, field, value)
    await db.commit()
    await db.refresh(med)
    return med


async def delete_medication(
    db: AsyncSession, clinic_id: uuid.UUID, med_id: uuid.UUID,
) -> bool:
    result = await db.execute(
        select(EncounterMedication).where(
            EncounterMedication.id == med_id,
            EncounterMedication.clinic_id == clinic_id,
        )
    )
    med = result.scalar_one_or_none()
    if not med:
        return False
    med.is_deleted = True
    await db.commit()
    return True


# ═════════════════════════════════════════════════════════════════════
#  7. Disposition CRUD
# ═════════════════════════════════════════════════════════════════════

async def create_disposition(
    db: AsyncSession, clinic_id: uuid.UUID, encounter_pk: uuid.UUID, payload: DispositionCreate,
) -> EncounterDisposition:
    disp = EncounterDisposition(clinic_id=clinic_id, encounter_id=encounter_pk, **payload.model_dump())
    db.add(disp)
    await db.commit()
    await db.refresh(disp)
    return disp


async def update_disposition(
    db: AsyncSession, clinic_id: uuid.UUID, disp_id: uuid.UUID, payload: DispositionUpdate,
) -> EncounterDisposition | None:
    result = await db.execute(
        select(EncounterDisposition).where(
            EncounterDisposition.id == disp_id,
            EncounterDisposition.clinic_id == clinic_id,
            EncounterDisposition.is_deleted.is_(False),
        )
    )
    disp = result.scalar_one_or_none()
    if not disp:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(disp, field, value)
    await db.commit()
    await db.refresh(disp)
    return disp


async def delete_disposition(
    db: AsyncSession, clinic_id: uuid.UUID, disp_id: uuid.UUID,
) -> bool:
    result = await db.execute(
        select(EncounterDisposition).where(
            EncounterDisposition.id == disp_id,
            EncounterDisposition.clinic_id == clinic_id,
        )
    )
    disp = result.scalar_one_or_none()
    if not disp:
        return False
    disp.is_deleted = True
    await db.commit()
    return True


# ═════════════════════════════════════════════════════════════════════
#  8. Status-only update
# ═════════════════════════════════════════════════════════════════════

async def update_encounter_status(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    encounter_id: uuid.UUID,
    payload: StatusUpdate,
) -> Encounter | None:
    encounter = await get_encounter_by_id(db=db, clinic_id=clinic_id, encounter_id=encounter_id)
    if not encounter:
        return None

    now = datetime.now(timezone.utc)
    triage_assessment_payload = (
        payload.triage_assessment.model_dump()
        if payload.triage_assessment is not None
        else None
    )

    if payload.status == "WITH_PROVIDER":
        if triage_assessment_payload:
            encounter.triage_assessment = triage_assessment_payload
        elif not encounter.triage_assessment:
            raise EncounterStatusTransitionError(
                "Detailed triage assessment is required before entering in-consultation."
            )

        encounter.triage_at = encounter.triage_at or now
        encounter.started_at = encounter.started_at or now
    elif payload.status == "TRIAGE":
        if triage_assessment_payload:
            encounter.triage_assessment = triage_assessment_payload
        encounter.triage_at = encounter.triage_at or now
    elif triage_assessment_payload:
        encounter.triage_assessment = triage_assessment_payload

    encounter.status = payload.status
    await db.commit()
    await db.refresh(encounter)
    return encounter


# ═════════════════════════════════════════════════════════════════════
#  9. Encounter queue (filterable)
# ═════════════════════════════════════════════════════════════════════

async def get_encounter_queue(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    page: int,
    size: int,
    department_id: uuid.UUID | None = None,
    status: str | None = None,
    queue_date: date | None = None,
    provider_id: uuid.UUID | None = None,
) -> tuple[list[Encounter], int]:
    target_date = queue_date or date.today()
    day_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)

    filters = [
        Encounter.clinic_id == clinic_id,
        Encounter.is_deleted.is_(False),
        Encounter.deleted_at.is_(None),
        Encounter.status.notin_(["DISCHARGED", "CANCELLED", "NO_SHOW"]) if not status else Encounter.status == status,
    ]

    # Scope to date via scheduled_at or created_at
    filters.append(
        or_(
            and_(Encounter.scheduled_at >= day_start, Encounter.scheduled_at <= day_end),
            and_(Encounter.scheduled_at.is_(None), Encounter.created_at >= day_start, Encounter.created_at <= day_end),
        )
    )

    if department_id:
        filters.append(Encounter.department_id == department_id)
    if provider_id:
        filters.append(Encounter.provider_id == provider_id)

    where_clause = and_(*filters)
    offset = (page - 1) * size

    total_result = await db.execute(
        select(func.count()).select_from(Encounter).where(where_clause)
    )
    total = total_result.scalar_one()

    # Order by triage urgency: TRIAGE first, then CHECKED_IN, etc.
    status_priority = case(
        (Encounter.status == "TRIAGE", 1),
        (Encounter.status == "CHECKED_IN", 2),
        (Encounter.status == "WITH_PROVIDER", 3),
        (Encounter.status == "PENDING_RESULTS", 4),
        (Encounter.status == "PENDING_REVIEW", 5),
        (Encounter.status == "SCHEDULED", 6),
        else_=7,
    )

    result = await db.execute(
        select(Encounter)
        .where(where_clause)
        .order_by(status_priority, Encounter.scheduled_at.asc().nullslast())
        .offset(offset)
        .limit(size)
    )
    return list(result.scalars().all()), total


# ═════════════════════════════════════════════════════════════════════
#  10. Today's encounters summary
# ═════════════════════════════════════════════════════════════════════

async def get_today_summary(
    db: AsyncSession, clinic_id: uuid.UUID,
) -> dict:
    today = date.today()
    day_start = datetime.combine(today, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(today, time.max, tzinfo=timezone.utc)

    base_filters = [
        Encounter.clinic_id == clinic_id,
        Encounter.is_deleted.is_(False),
        or_(
            and_(Encounter.scheduled_at >= day_start, Encounter.scheduled_at <= day_end),
            and_(Encounter.scheduled_at.is_(None), Encounter.created_at >= day_start, Encounter.created_at <= day_end),
        ),
    ]
    where_clause = and_(*base_filters)

    total_result = await db.execute(
        select(func.count()).select_from(Encounter).where(where_clause)
    )
    total = total_result.scalar_one()

    status_result = await db.execute(
        select(Encounter.status, func.count())
        .where(where_clause)
        .group_by(Encounter.status)
    )
    by_status = {row[0]: row[1] for row in status_result.all()}

    type_result = await db.execute(
        select(Encounter.encounter_type, func.count())
        .where(where_clause)
        .group_by(Encounter.encounter_type)
    )
    by_type = {row[0]: row[1] for row in type_result.all()}

    return {"total": total, "by_status": by_status, "by_type": by_type}


# ═════════════════════════════════════════════════════════════════════
#  11. Patient encounter history
# ═════════════════════════════════════════════════════════════════════

async def get_patient_encounters(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    page: int,
    size: int,
) -> tuple[list[Encounter], int]:
    filters = [
        Encounter.clinic_id == clinic_id,
        Encounter.patient_id == patient_id,
        Encounter.is_deleted.is_(False),
        Encounter.deleted_at.is_(None),
    ]
    where_clause = and_(*filters)
    offset = (page - 1) * size

    total_result = await db.execute(
        select(func.count()).select_from(Encounter).where(where_clause)
    )
    total = total_result.scalar_one()

    result = await db.execute(
        select(Encounter)
        .where(where_clause)
        .order_by(Encounter.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    return list(result.scalars().all()), total


# ═════════════════════════════════════════════════════════════════════
#  12. List sub-resources
# ═════════════════════════════════════════════════════════════════════

async def list_vitals(
    db: AsyncSession, clinic_id: uuid.UUID, encounter_pk: uuid.UUID,
) -> list[EncounterVitals]:
    result = await db.execute(
        select(EncounterVitals).where(
            EncounterVitals.encounter_id == encounter_pk,
            EncounterVitals.clinic_id == clinic_id,
            EncounterVitals.is_deleted.is_(False),
        ).order_by(EncounterVitals.recorded_at.desc().nullslast())
    )
    return list(result.scalars().all())


async def list_notes(
    db: AsyncSession, clinic_id: uuid.UUID, encounter_pk: uuid.UUID,
) -> list[EncounterNote]:
    result = await db.execute(
        select(EncounterNote).where(
            EncounterNote.encounter_id == encounter_pk,
            EncounterNote.clinic_id == clinic_id,
            EncounterNote.is_deleted.is_(False),
        ).order_by(EncounterNote.created_at.desc())
    )
    return list(result.scalars().all())


async def list_diagnoses(
    db: AsyncSession, clinic_id: uuid.UUID, encounter_pk: uuid.UUID,
) -> list[EncounterDiagnosis]:
    result = await db.execute(
        select(EncounterDiagnosis).where(
            EncounterDiagnosis.encounter_id == encounter_pk,
            EncounterDiagnosis.clinic_id == clinic_id,
            EncounterDiagnosis.is_deleted.is_(False),
        ).order_by(EncounterDiagnosis.created_at.desc())
    )
    return list(result.scalars().all())


async def list_orders(
    db: AsyncSession, clinic_id: uuid.UUID, encounter_pk: uuid.UUID,
) -> list[EncounterOrder]:
    result = await db.execute(
        select(EncounterOrder).where(
            EncounterOrder.encounter_id == encounter_pk,
            EncounterOrder.clinic_id == clinic_id,
            EncounterOrder.is_deleted.is_(False),
        ).order_by(EncounterOrder.created_at.desc())
    )
    return list(result.scalars().all())


async def list_medications(
    db: AsyncSession, clinic_id: uuid.UUID, encounter_pk: uuid.UUID,
) -> list[EncounterMedication]:
    result = await db.execute(
        select(EncounterMedication).where(
            EncounterMedication.encounter_id == encounter_pk,
            EncounterMedication.clinic_id == clinic_id,
            EncounterMedication.is_deleted.is_(False),
        ).order_by(EncounterMedication.created_at.desc())
    )
    return list(result.scalars().all())


async def get_disposition(
    db: AsyncSession, clinic_id: uuid.UUID, encounter_pk: uuid.UUID,
) -> EncounterDisposition | None:
    result = await db.execute(
        select(EncounterDisposition).where(
            EncounterDisposition.encounter_id == encounter_pk,
            EncounterDisposition.clinic_id == clinic_id,
            EncounterDisposition.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()


# ═════════════════════════════════════════════════════════════════════
#  13. Sign note (locks editing)
# ═════════════════════════════════════════════════════════════════════

async def sign_note(
    db: AsyncSession, clinic_id: uuid.UUID, note_id: uuid.UUID,
) -> EncounterNote | None:
    result = await db.execute(
        select(EncounterNote).where(
            EncounterNote.id == note_id,
            EncounterNote.clinic_id == clinic_id,
            EncounterNote.is_deleted.is_(False),
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        return None
    if note.is_signed:
        return note  # Already signed
    note.is_signed = True
    note.signed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(note)
    return note
