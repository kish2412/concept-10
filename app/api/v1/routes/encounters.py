"""Encounter API routes."""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_ai_enabled
from app.core.audit import audit_log
from app.core.database import get_db
from app.core.rbac import (
    UserContext,
    get_user_context,
    require_permission, require_role,
)
from app.models.rbac import PermissionAction, PermissionResource
from app.models.clinic import Clinic
from app.models.user import UserRole
from app.schemas.encounter import (
    DiagnosisCreate,
    DiagnosisResponse,
    DiagnosisUpdate,
    DispositionCreate,
    DispositionResponse,
    DispositionUpdate,
    EncounterCreate, EncounterListResponse, EncounterResponse,
    MedicationCreate,
    MedicationResponse,
    MedicationUpdate,
    NoteCreate,
    NoteResponse,
    NoteUpdate,
    OrderCreate,
    OrderResponse,
    OrderUpdate,
    EncounterUpdate, StatusUpdate, TodaySummary,
    TriageSummaryGenerateRequest, TriageSummaryResponse,
    VitalsCreate,
    VitalsResponse,
    VitalsUpdate,
)
from app.services import agentic_triage_service
from app.services import encounter_service as svc

router = APIRouter()

_can_read = Depends(require_permission(PermissionAction.READ, PermissionResource.PATIENT))
_can_update_encounter = Depends(
    require_permission(PermissionAction.UPDATE, PermissionResource.CLINICAL_NOTES)
)
_can_manage_vitals = Depends(
    require_permission(PermissionAction.CREATE, PermissionResource.VITALS)
)
_can_manage_notes = Depends(
    require_permission(PermissionAction.CREATE, PermissionResource.CLINICAL_NOTES)
)
_can_manage_investigations = Depends(
    require_permission(PermissionAction.CREATE, PermissionResource.INVESTIGATION)
)
_can_manage_prescriptions = Depends(
    require_permission(PermissionAction.CREATE, PermissionResource.PRESCRIPTION)
)
_can_delete = Depends(require_role(UserRole.ADMIN))


# ── Encounter CRUD ────────────────────────────────────────────────────

@router.post(
    "",
    response_model=EncounterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_permission(PermissionAction.CREATE, PermissionResource.CHECKIN)),
        Depends(audit_log),
    ],
)
async def create_encounter(
    payload: EncounterCreate,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> EncounterResponse:
    return await svc.create_encounter(db=db, clinic_id=ctx.clinic_uuid, payload=payload)


@router.get(
    "/queue",
    response_model=EncounterListResponse,
    dependencies=[Depends(require_permission(PermissionAction.READ, PermissionResource.QUEUE))],
)
async def encounter_queue(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=100),
    department_id: uuid.UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    queue_date: date | None = Query(default=None, alias="date"),
    provider_id: uuid.UUID | None = Query(default=None),
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> EncounterListResponse:
    items, total = await svc.get_encounter_queue(
        db=db, clinic_id=ctx.clinic_uuid, page=page, size=size,
        department_id=department_id, status=status_filter,
        queue_date=queue_date, provider_id=provider_id,
    )
    return EncounterListResponse(items=items, page=page, size=size, total=total)


@router.get("/today", response_model=TodaySummary, dependencies=[_can_read])
async def today_summary(ctx: UserContext = Depends(get_user_context), db: AsyncSession = Depends(get_db)):
    return TodaySummary(**(await svc.get_today_summary(db=db, clinic_id=ctx.clinic_uuid)))


@router.get("", response_model=EncounterListResponse, dependencies=[_can_read])
async def list_encounters(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    encounter_type: str | None = Query(default=None),
    patient_id: uuid.UUID | None = Query(default=None),
    provider_id: uuid.UUID | None = Query(default=None),
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> EncounterListResponse:
    items, total = await svc.list_encounters(
        db=db, clinic_id=ctx.clinic_uuid, page=page, size=size,
        search=search, status=status_filter,
        encounter_type=encounter_type, patient_id=patient_id, provider_id=provider_id,
    )
    return EncounterListResponse(items=items, page=page, size=size, total=total)


@router.get("/patient/{patient_id}", response_model=EncounterListResponse, dependencies=[_can_read])
async def patient_encounter_history(
    patient_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> EncounterListResponse:
    items, total = await svc.get_patient_encounters(
        db=db,
        clinic_id=ctx.clinic_uuid,
        patient_id=patient_id,
        page=page,
        size=size,
    )
    return EncounterListResponse(items=items, page=page, size=size, total=total)


@router.get("/{id}", response_model=EncounterResponse, dependencies=[_can_read])
async def get_encounter(
    id: uuid.UUID,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> EncounterResponse:
    enc = await svc.get_encounter_by_id(db=db, clinic_id=ctx.clinic_uuid, encounter_id=id)
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return enc


@router.patch(
    "/{id}/status",
    response_model=EncounterResponse,
    dependencies=[
        Depends(require_permission(PermissionAction.UPDATE, PermissionResource.CHECKIN)),
        Depends(audit_log),
    ],
)
async def update_status(
    id: uuid.UUID,
    payload: StatusUpdate,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> EncounterResponse:
    try:
        enc = await svc.update_encounter_status(db=db, clinic_id=ctx.clinic_uuid, encounter_id=id, payload=payload)
    except svc.EncounterStatusTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return enc


@router.put("/{id}", response_model=EncounterResponse, dependencies=[_can_update_encounter, Depends(audit_log)])
async def update_encounter(
    id: uuid.UUID,
    payload: EncounterUpdate,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> EncounterResponse:
    enc = await svc.update_encounter(db=db, clinic_id=ctx.clinic_uuid, encounter_id=id, payload=payload)
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return enc


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_can_delete, Depends(audit_log)])
async def delete_encounter(
    id: uuid.UUID,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not await svc.soft_delete_encounter(db=db, clinic_id=ctx.clinic_uuid, encounter_id=id):
        raise HTTPException(status_code=404, detail="Encounter not found")


@router.post(
    "/{id}/vitals",
    response_model=VitalsResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_can_manage_vitals, Depends(audit_log)],
)
async def add_vitals(
    id: uuid.UUID,
    payload: VitalsCreate,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> VitalsResponse:
    return await svc.create_vitals(db=db, clinic_id=ctx.clinic_uuid, encounter_pk=id, payload=payload)


@router.get("/{id}/vitals", response_model=list[VitalsResponse], dependencies=[_can_read])
async def get_vitals(
    id: uuid.UUID,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> list[VitalsResponse]:
    return await svc.list_vitals(db=db, clinic_id=ctx.clinic_uuid, encounter_pk=id)


@router.put(
    "/{id}/vitals/{vitals_id}",
    response_model=VitalsResponse,
    dependencies=[_can_manage_vitals, Depends(audit_log)],
)
async def update_vitals_record(
    id: uuid.UUID,
    vitals_id: uuid.UUID,
    payload: VitalsUpdate,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> VitalsResponse:
    result = await svc.update_vitals(db=db, clinic_id=ctx.clinic_uuid, vitals_id=vitals_id, payload=payload)
    if not result:
        raise HTTPException(status_code=404, detail="Vitals record not found")
    return result


@router.delete("/{id}/vitals/{vitals_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(audit_log)])
async def delete_vitals_record(
    id: uuid.UUID,
    vitals_id: uuid.UUID,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not await svc.delete_vitals(db=db, clinic_id=ctx.clinic_uuid, vitals_id=vitals_id):
        raise HTTPException(status_code=404, detail="Vitals record not found")


@router.post(
    "/{id}/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_can_manage_notes, Depends(audit_log)],
)
async def add_note(
    id: uuid.UUID,
    payload: NoteCreate,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> NoteResponse:
    return await svc.create_note(db=db, clinic_id=ctx.clinic_uuid, encounter_pk=id, payload=payload)


@router.get("/{id}/notes", response_model=list[NoteResponse], dependencies=[_can_read])
async def get_notes(
    id: uuid.UUID,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> list[NoteResponse]:
    return await svc.list_notes(db=db, clinic_id=ctx.clinic_uuid, encounter_pk=id)


@router.post(
    "/{id}/notes/{note_id}/sign",
    response_model=NoteResponse,
    dependencies=[_can_manage_notes, Depends(audit_log)],
)
async def sign_note_record(
    id: uuid.UUID,
    note_id: uuid.UUID,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> NoteResponse:
    note = await svc.sign_note(db=db, clinic_id=ctx.clinic_uuid, note_id=note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.put(
    "/{id}/notes/{note_id}",
    response_model=NoteResponse,
    dependencies=[_can_manage_notes, Depends(audit_log)],
)
async def update_note_record(
    id: uuid.UUID,
    note_id: uuid.UUID,
    payload: NoteUpdate,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> NoteResponse:
    result = await svc.update_note(db=db, clinic_id=ctx.clinic_uuid, note_id=note_id, payload=payload)
    if not result:
        raise HTTPException(status_code=404, detail="Note not found")
    return result


@router.delete("/{id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(audit_log)])
async def delete_note_record(
    id: uuid.UUID,
    note_id: uuid.UUID,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not await svc.delete_note(db=db, clinic_id=ctx.clinic_uuid, note_id=note_id):
        raise HTTPException(status_code=404, detail="Note not found")


@router.post(
    "/{id}/diagnoses",
    response_model=DiagnosisResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_can_manage_investigations, Depends(audit_log)],
)
async def add_diagnosis(
    id: uuid.UUID,
    payload: DiagnosisCreate,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> DiagnosisResponse:
    return await svc.create_diagnosis(db=db, clinic_id=ctx.clinic_uuid, encounter_pk=id, payload=payload)


@router.get("/{id}/diagnoses", response_model=list[DiagnosisResponse], dependencies=[_can_read])
async def get_diagnoses(
    id: uuid.UUID,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> list[DiagnosisResponse]:
    return await svc.list_diagnoses(db=db, clinic_id=ctx.clinic_uuid, encounter_pk=id)


@router.put(
    "/{id}/diagnoses/{dx_id}",
    response_model=DiagnosisResponse,
    dependencies=[_can_manage_investigations, Depends(audit_log)],
)
async def update_diagnosis_record(
    id: uuid.UUID,
    dx_id: uuid.UUID,
    payload: DiagnosisUpdate,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> DiagnosisResponse:
    result = await svc.update_diagnosis(db=db, clinic_id=ctx.clinic_uuid, dx_id=dx_id, payload=payload)
    if not result:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    return result


@router.delete(
    "/{id}/diagnoses/{dx_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_can_manage_investigations, Depends(audit_log)],
)
async def delete_diagnosis_record(
    id: uuid.UUID,
    dx_id: uuid.UUID,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not await svc.delete_diagnosis(db=db, clinic_id=ctx.clinic_uuid, dx_id=dx_id):
        raise HTTPException(status_code=404, detail="Diagnosis not found")


@router.post(
    "/{id}/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_can_manage_investigations, Depends(audit_log)],
)
async def add_order(
    id: uuid.UUID,
    payload: OrderCreate,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    return await svc.create_order(db=db, clinic_id=ctx.clinic_uuid, encounter_pk=id, payload=payload)


@router.get("/{id}/orders", response_model=list[OrderResponse], dependencies=[_can_read])
async def get_orders(
    id: uuid.UUID,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> list[OrderResponse]:
    return await svc.list_orders(db=db, clinic_id=ctx.clinic_uuid, encounter_pk=id)


@router.patch(
    "/{id}/orders/{order_id}",
    response_model=OrderResponse,
    dependencies=[_can_manage_investigations, Depends(audit_log)],
)
async def update_order_record(
    id: uuid.UUID,
    order_id: uuid.UUID,
    payload: OrderUpdate,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    result = await svc.update_order(db=db, clinic_id=ctx.clinic_uuid, order_id=order_id, payload=payload)
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    return result


@router.delete(
    "/{id}/orders/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_can_manage_investigations, Depends(audit_log)],
)
async def delete_order_record(
    id: uuid.UUID,
    order_id: uuid.UUID,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not await svc.delete_order(db=db, clinic_id=ctx.clinic_uuid, order_id=order_id):
        raise HTTPException(status_code=404, detail="Order not found")


@router.post(
    "/{id}/medications",
    response_model=MedicationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_can_manage_prescriptions, Depends(audit_log)],
)
async def add_medication(
    id: uuid.UUID,
    payload: MedicationCreate,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> MedicationResponse:
    return await svc.create_medication(db=db, clinic_id=ctx.clinic_uuid, encounter_pk=id, payload=payload)


@router.get("/{id}/medications", response_model=list[MedicationResponse], dependencies=[_can_read])
async def get_medications(
    id: uuid.UUID,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> list[MedicationResponse]:
    return await svc.list_medications(db=db, clinic_id=ctx.clinic_uuid, encounter_pk=id)


@router.put(
    "/{id}/medications/{med_id}",
    response_model=MedicationResponse,
    dependencies=[_can_manage_prescriptions, Depends(audit_log)],
)
async def update_medication_record(
    id: uuid.UUID,
    med_id: uuid.UUID,
    payload: MedicationUpdate,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> MedicationResponse:
    result = await svc.update_medication(db=db, clinic_id=ctx.clinic_uuid, med_id=med_id, payload=payload)
    if not result:
        raise HTTPException(status_code=404, detail="Medication not found")
    return result


@router.delete(
    "/{id}/medications/{med_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_can_manage_prescriptions, Depends(audit_log)],
)
async def delete_medication_record(
    id: uuid.UUID,
    med_id: uuid.UUID,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not await svc.delete_medication(db=db, clinic_id=ctx.clinic_uuid, med_id=med_id):
        raise HTTPException(status_code=404, detail="Medication not found")


@router.post(
    "/{id}/disposition",
    response_model=DispositionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_can_manage_notes, Depends(audit_log)],
)
async def add_disposition(
    id: uuid.UUID,
    payload: DispositionCreate,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> DispositionResponse:
    return await svc.create_disposition(db=db, clinic_id=ctx.clinic_uuid, encounter_pk=id, payload=payload)


@router.get("/{id}/disposition", response_model=DispositionResponse | None, dependencies=[_can_read])
async def get_disposition_record(
    id: uuid.UUID,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> DispositionResponse | None:
    return await svc.get_disposition(db=db, clinic_id=ctx.clinic_uuid, encounter_pk=id)


@router.put(
    "/{id}/disposition/{disp_id}",
    response_model=DispositionResponse,
    dependencies=[_can_manage_notes, Depends(audit_log)],
)
async def update_disposition_record(
    id: uuid.UUID,
    disp_id: uuid.UUID,
    payload: DispositionUpdate,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> DispositionResponse:
    result = await svc.update_disposition(db=db, clinic_id=ctx.clinic_uuid, disp_id=disp_id, payload=payload)
    if not result:
        raise HTTPException(status_code=404, detail="Disposition not found")
    return result


@router.delete(
    "/{id}/disposition/{disp_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_can_manage_notes, Depends(audit_log)],
)
async def delete_disposition_record(
    id: uuid.UUID,
    disp_id: uuid.UUID,
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not await svc.delete_disposition(db=db, clinic_id=ctx.clinic_uuid, disp_id=disp_id):
        raise HTTPException(status_code=404, detail="Disposition not found")


# ── AI endpoints ──────────────────────────────────────────────────────

@router.post(
    "/{id}/ai/triage-summary",
    response_model=TriageSummaryResponse,
    dependencies=[
        Depends(require_permission(PermissionAction.READ, PermissionResource.CLINICAL_NOTES)),
        Depends(audit_log),
    ],
)
async def generate_triage_summary(
    id: uuid.UUID,
    payload: TriageSummaryGenerateRequest,
    clinic: Clinic = Depends(require_ai_enabled),
    db: AsyncSession = Depends(get_db),
) -> TriageSummaryResponse:
    result = await agentic_triage_service.generate_triage_summary(
        db=db, clinic_id=clinic.id, encounter_id=id,
        guardrail_profile=clinic.ai_guardrail_profile,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return TriageSummaryResponse(
        encounter_id=result.encounter_id, summary=result.summary,
        clinician_focus_points=result.clinician_focus_points, red_flags=result.red_flags,
        missing_information=result.missing_information, generated_at=result.generated_at,
        orchestration=result.orchestration, model_provider=result.model_provider,
        model_name=result.model_name, guardrail_profile=result.guardrail_profile,
        langsmith_trace_url=result.langsmith_trace_url,
    )

