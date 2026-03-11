"""
Encounter module — full REST API.

All write endpoints enforce RBAC via ``authorize_role`` and emit an audit
log entry via the ``audit_log`` dependency.  Sub-resource routes use
``validate_encounter_exists`` to verify the parent encounter before
operating on children.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, require_ai_feature_enabled, validate_encounter_exists
from app.core.audit import audit_log
from app.core.database import get_db
from app.core.rbac import authorize_role
from app.schemas.encounter import (
    AgentInvocationRequest,
    DiagnosisCreate,
    DiagnosisResponse,
    DiagnosisUpdate,
    DifferentialDiagnosisResponse,
    DispositionRiskResponse,
    DocumentationQualityResponse,
    DispositionCreate,
    DispositionResponse,
    DispositionUpdate,
    EncounterCreate,
    EncounterListResponse,
    EncounterResponse,
    EncounterUpdate,
    MedicationCreate,
    MedicationSafetyResponse,
    MedicationResponse,
    MedicationUpdate,
    NoteCreate,
    NoteResponse,
    NoteUpdate,
    OrderRecommendationResponse,
    OrderCreate,
    OrderResponse,
    OrderUpdate,
    PriorEncounterSummaryResponse,
    StatusUpdate,
    TodaySummary,
    TriageSummaryGenerateRequest,
    TriageSummaryResponse,
    VitalsCreate,
    VitalsResponse,
    VitalsUpdate,
)
from app.models.clinic import Clinic
from app.services import agentic_clinical_agents_service
from app.services import agentic_triage_service
from app.services import encounter_service as svc

router = APIRouter()


def _parse_clinic_uuid(clinic_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(clinic_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tenant context",
        ) from exc


# ═════════════════════════════════════════════════════════════════════
#  Encounter CRUD
# ═════════════════════════════════════════════════════════════════════

@router.post(
    "",
    response_model=EncounterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(authorize_role("admin", "provider", "nurse")), Depends(audit_log)],
    summary="Create new encounter",
)
async def create_encounter_record(
    payload: EncounterCreate,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EncounterResponse:
    """Create a new encounter for a patient."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    return await svc.create_encounter(db=db, clinic_id=clinic_uuid, payload=payload)


@router.get(
    "/queue",
    response_model=EncounterListResponse,
    dependencies=[Depends(authorize_role("admin", "provider", "nurse", "viewer"))],
    summary="Live encounter queue",
)
async def encounter_queue(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=100),
    department_id: uuid.UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    queue_date: date | None = Query(default=None, alias="date"),
    provider_id: uuid.UUID | None = Query(default=None),
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EncounterListResponse:
    """Filterable live encounter queue ordered by triage urgency."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    items, total = await svc.get_encounter_queue(
        db=db,
        clinic_id=clinic_uuid,
        page=page,
        size=size,
        department_id=department_id,
        status=status_filter,
        queue_date=queue_date,
        provider_id=provider_id,
    )
    return EncounterListResponse(items=items, page=page, size=size, total=total)


@router.get(
    "/today",
    response_model=TodaySummary,
    dependencies=[Depends(authorize_role("admin", "provider", "nurse", "viewer"))],
    summary="Today's encounters summary",
)
async def today_summary(
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> TodaySummary:
    """Aggregate counts of today's encounters by status and type."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    data = await svc.get_today_summary(db=db, clinic_id=clinic_uuid)
    return TodaySummary(**data)


@router.get(
    "/patient/{patient_id}",
    response_model=EncounterListResponse,
    dependencies=[Depends(authorize_role("admin", "provider", "nurse", "viewer"))],
    summary="Patient encounter history",
)
async def patient_encounter_history(
    patient_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EncounterListResponse:
    """Paginated encounter history for a specific patient."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    items, total = await svc.get_patient_encounters(
        db=db, clinic_id=clinic_uuid, patient_id=patient_id, page=page, size=size,
    )
    return EncounterListResponse(items=items, page=page, size=size, total=total)


@router.get(
    "",
    response_model=EncounterListResponse,
    dependencies=[Depends(authorize_role("admin", "provider", "nurse", "viewer"))],
    summary="List encounters",
)
async def get_encounters(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    encounter_type: str | None = Query(default=None),
    patient_id: uuid.UUID | None = Query(default=None),
    provider_id: uuid.UUID | None = Query(default=None),
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EncounterListResponse:
    """Search & paginate encounters with optional filters."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    items, total = await svc.list_encounters(
        db=db,
        clinic_id=clinic_uuid,
        page=page,
        size=size,
        search=search,
        status=status_filter,
        encounter_type=encounter_type,
        patient_id=patient_id,
        provider_id=provider_id,
    )
    return EncounterListResponse(items=items, page=page, size=size, total=total)


@router.get(
    "/{id}",
    response_model=EncounterResponse,
    dependencies=[Depends(authorize_role("admin", "provider", "nurse", "viewer"))],
    summary="Get encounter by ID (full detail)",
)
async def get_encounter(
    id: uuid.UUID,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EncounterResponse:
    """Return full encounter detail including all nested sub-resources."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    encounter = await svc.get_encounter_by_id(db=db, clinic_id=clinic_uuid, encounter_id=id)
    if not encounter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")
    return encounter


@router.post(
    "/{id}/ai/triage-summary",
    response_model=TriageSummaryResponse,
    dependencies=[Depends(authorize_role("admin", "provider", "nurse")), Depends(audit_log)],
    summary="Generate AI summary for post-triage encounter review",
)
async def generate_triage_summary(
    id: uuid.UUID,
    payload: TriageSummaryGenerateRequest,
    clinic: Clinic = Depends(require_ai_feature_enabled),
    db: AsyncSession = Depends(get_db),
) -> TriageSummaryResponse:
    """Generate a clinician-facing summary from triage context for diagnostic review."""
    _ = payload.regenerate
    result = await agentic_triage_service.generate_triage_summary(
        db=db,
        clinic_id=clinic.id,
        encounter_id=id,
        guardrail_profile=clinic.ai_guardrail_profile,
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")

    return TriageSummaryResponse(
        encounter_id=result.encounter_id,
        summary=result.summary,
        clinician_focus_points=result.clinician_focus_points,
        red_flags=result.red_flags,
        missing_information=result.missing_information,
        generated_at=result.generated_at,
        orchestration=result.orchestration,
        model_provider=result.model_provider,
        model_name=result.model_name,
        guardrail_profile=result.guardrail_profile,
        langsmith_trace_url=result.langsmith_trace_url,
    )


@router.post(
    "/{id}/ai/differential-diagnosis",
    response_model=DifferentialDiagnosisResponse,
    dependencies=[Depends(authorize_role("admin", "provider", "nurse")), Depends(audit_log)],
    summary="Generate differential diagnosis shortlist",
)
async def generate_differential_diagnosis(
    id: uuid.UUID,
    payload: AgentInvocationRequest,
    clinic: Clinic = Depends(require_ai_feature_enabled),
    db: AsyncSession = Depends(get_db),
) -> DifferentialDiagnosisResponse:
    _ = payload.regenerate
    result = await agentic_clinical_agents_service.run_differential_diagnosis_agent(
        db=db,
        clinic_id=clinic.id,
        encounter_id=id,
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")
    return DifferentialDiagnosisResponse(**result, guardrail_profile=clinic.ai_guardrail_profile)


@router.post(
    "/{id}/ai/orders-recommendation",
    response_model=OrderRecommendationResponse,
    dependencies=[Depends(authorize_role("admin", "provider", "nurse")), Depends(audit_log)],
    summary="Generate recommended diagnostic/therapeutic orders",
)
async def generate_orders_recommendation(
    id: uuid.UUID,
    payload: AgentInvocationRequest,
    clinic: Clinic = Depends(require_ai_feature_enabled),
    db: AsyncSession = Depends(get_db),
) -> OrderRecommendationResponse:
    _ = payload.regenerate
    result = await agentic_clinical_agents_service.run_order_recommendation_agent(
        db=db,
        clinic_id=clinic.id,
        encounter_id=id,
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")
    return OrderRecommendationResponse(**result, guardrail_profile=clinic.ai_guardrail_profile)


@router.post(
    "/{id}/ai/medication-safety",
    response_model=MedicationSafetyResponse,
    dependencies=[Depends(authorize_role("admin", "provider", "nurse")), Depends(audit_log)],
    summary="Run medication safety checks",
)
async def generate_medication_safety(
    id: uuid.UUID,
    payload: AgentInvocationRequest,
    clinic: Clinic = Depends(require_ai_feature_enabled),
    db: AsyncSession = Depends(get_db),
) -> MedicationSafetyResponse:
    _ = payload.regenerate
    result = await agentic_clinical_agents_service.run_medication_safety_agent(
        db=db,
        clinic_id=clinic.id,
        encounter_id=id,
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")
    return MedicationSafetyResponse(**result, guardrail_profile=clinic.ai_guardrail_profile)


@router.post(
    "/{id}/ai/disposition-risk",
    response_model=DispositionRiskResponse,
    dependencies=[Depends(authorize_role("admin", "provider", "nurse")), Depends(audit_log)],
    summary="Estimate disposition/readmission risk",
)
async def generate_disposition_risk(
    id: uuid.UUID,
    payload: AgentInvocationRequest,
    clinic: Clinic = Depends(require_ai_feature_enabled),
    db: AsyncSession = Depends(get_db),
) -> DispositionRiskResponse:
    _ = payload.regenerate
    result = await agentic_clinical_agents_service.run_disposition_risk_agent(
        db=db,
        clinic_id=clinic.id,
        encounter_id=id,
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")
    return DispositionRiskResponse(**result, guardrail_profile=clinic.ai_guardrail_profile)


@router.post(
    "/{id}/ai/documentation-quality",
    response_model=DocumentationQualityResponse,
    dependencies=[Depends(authorize_role("admin", "provider", "nurse")), Depends(audit_log)],
    summary="Assess encounter documentation quality",
)
async def generate_documentation_quality(
    id: uuid.UUID,
    payload: AgentInvocationRequest,
    clinic: Clinic = Depends(require_ai_feature_enabled),
    db: AsyncSession = Depends(get_db),
) -> DocumentationQualityResponse:
    _ = payload.regenerate
    result = await agentic_clinical_agents_service.run_documentation_quality_agent(
        db=db,
        clinic_id=clinic.id,
        encounter_id=id,
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")
    return DocumentationQualityResponse(**result, guardrail_profile=clinic.ai_guardrail_profile)


@router.post(
    "/{id}/ai/prior-encounter-summary",
    response_model=PriorEncounterSummaryResponse,
    dependencies=[Depends(authorize_role("admin", "provider", "nurse")), Depends(audit_log)],
    summary="Summarize prior encounters and recurring patterns",
)
async def generate_prior_encounter_summary(
    id: uuid.UUID,
    payload: AgentInvocationRequest,
    clinic: Clinic = Depends(require_ai_feature_enabled),
    db: AsyncSession = Depends(get_db),
) -> PriorEncounterSummaryResponse:
    _ = payload.regenerate
    result = await agentic_clinical_agents_service.run_prior_encounter_summary_agent(
        db=db,
        clinic_id=clinic.id,
        encounter_id=id,
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")
    return PriorEncounterSummaryResponse(**result, guardrail_profile=clinic.ai_guardrail_profile)


@router.patch(
    "/{id}/status",
    response_model=EncounterResponse,
    dependencies=[Depends(authorize_role("admin", "provider", "nurse")), Depends(audit_log)],
    summary="Update encounter status",
)
async def update_encounter_status(
    id: uuid.UUID,
    payload: StatusUpdate,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EncounterResponse:
    """Transition the encounter to a new status."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    try:
        encounter = await svc.update_encounter_status(
            db=db, clinic_id=clinic_uuid, encounter_id=id, payload=payload,
        )
    except svc.EncounterStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not encounter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")
    return encounter


@router.put(
    "/{id}",
    response_model=EncounterResponse,
    dependencies=[Depends(authorize_role("admin", "provider")), Depends(audit_log)],
    summary="Update encounter",
)
async def update_encounter_record(
    id: uuid.UUID,
    payload: EncounterUpdate,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EncounterResponse:
    """Update encounter fields."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    encounter = await svc.update_encounter(db=db, clinic_id=clinic_uuid, encounter_id=id, payload=payload)
    if not encounter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")
    return encounter


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(authorize_role("admin")), Depends(audit_log)],
    summary="Soft delete encounter (admin only)",
)
async def delete_encounter_record(
    id: uuid.UUID,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete an encounter. Restricted to admin role."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    deleted = await svc.soft_delete_encounter(db=db, clinic_id=clinic_uuid, encounter_id=id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")


# ═════════════════════════════════════════════════════════════════════
#  Vitals
# ═════════════════════════════════════════════════════════════════════

@router.post(
    "/{id}/vitals",
    response_model=VitalsResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider", "nurse")),
        Depends(audit_log),
    ],
    summary="Record vitals (nurse role)",
)
async def add_vitals(
    id: uuid.UUID,
    payload: VitalsCreate,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> VitalsResponse:
    """Record a new vitals reading for an encounter."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    return await svc.create_vitals(db=db, clinic_id=clinic_uuid, encounter_pk=id, payload=payload)


@router.get(
    "/{id}/vitals",
    response_model=list[VitalsResponse],
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider", "nurse", "viewer")),
    ],
    summary="Get vitals history for encounter",
)
async def get_vitals(
    id: uuid.UUID,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[VitalsResponse]:
    """Return all vitals recordings for an encounter, newest first."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    return await svc.list_vitals(db=db, clinic_id=clinic_uuid, encounter_pk=id)


@router.put(
    "/{id}/vitals/{vitals_id}",
    response_model=VitalsResponse,
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider", "nurse")),
        Depends(audit_log),
    ],
    summary="Update vitals record",
)
async def update_vitals_record(
    id: uuid.UUID,
    vitals_id: uuid.UUID,
    payload: VitalsUpdate,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> VitalsResponse:
    """Update an existing vitals record."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    result = await svc.update_vitals(db=db, clinic_id=clinic_uuid, vitals_id=vitals_id, payload=payload)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vitals record not found")
    return result


@router.delete(
    "/{id}/vitals/{vitals_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin")),
        Depends(audit_log),
    ],
    summary="Delete vitals record",
)
async def delete_vitals_record(
    id: uuid.UUID,
    vitals_id: uuid.UUID,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a vitals record."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    if not await svc.delete_vitals(db=db, clinic_id=clinic_uuid, vitals_id=vitals_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vitals record not found")


# ═════════════════════════════════════════════════════════════════════
#  Clinical Notes
# ═════════════════════════════════════════════════════════════════════

@router.post(
    "/{id}/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider")),
        Depends(audit_log),
    ],
    summary="Create/update SOAP note",
)
async def add_note(
    id: uuid.UUID,
    payload: NoteCreate,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> NoteResponse:
    """Create a new clinical note (SOAP/progress/procedure/discharge)."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    return await svc.create_note(db=db, clinic_id=clinic_uuid, encounter_pk=id, payload=payload)


@router.get(
    "/{id}/notes",
    response_model=list[NoteResponse],
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider", "nurse", "viewer")),
    ],
    summary="Get all notes for encounter",
)
async def get_notes(
    id: uuid.UUID,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[NoteResponse]:
    """Return all clinical notes for an encounter."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    return await svc.list_notes(db=db, clinic_id=clinic_uuid, encounter_pk=id)


@router.post(
    "/{id}/notes/{note_id}/sign",
    response_model=NoteResponse,
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider")),
        Depends(audit_log),
    ],
    summary="Sign a note (locks editing)",
)
async def sign_note_record(
    id: uuid.UUID,
    note_id: uuid.UUID,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> NoteResponse:
    """Sign a clinical note, permanently locking it from further edits."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    note = await svc.sign_note(db=db, clinic_id=clinic_uuid, note_id=note_id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


@router.put(
    "/{id}/notes/{note_id}",
    response_model=NoteResponse,
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider")),
        Depends(audit_log),
    ],
    summary="Update clinical note",
)
async def update_note_record(
    id: uuid.UUID,
    note_id: uuid.UUID,
    payload: NoteUpdate,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> NoteResponse:
    """Update a clinical note. Fails if the note is already signed."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    result = await svc.update_note(db=db, clinic_id=clinic_uuid, note_id=note_id, payload=payload)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return result


@router.delete(
    "/{id}/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin")),
        Depends(audit_log),
    ],
    summary="Delete clinical note",
)
async def delete_note_record(
    id: uuid.UUID,
    note_id: uuid.UUID,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a clinical note."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    if not await svc.delete_note(db=db, clinic_id=clinic_uuid, note_id=note_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")


# ═════════════════════════════════════════════════════════════════════
#  Diagnoses
# ═════════════════════════════════════════════════════════════════════

@router.post(
    "/{id}/diagnoses",
    response_model=DiagnosisResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider")),
        Depends(audit_log),
    ],
    summary="Add diagnosis (ICD code)",
)
async def add_diagnosis(
    id: uuid.UUID,
    payload: DiagnosisCreate,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> DiagnosisResponse:
    """Add a diagnosis with ICD code to an encounter."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    return await svc.create_diagnosis(db=db, clinic_id=clinic_uuid, encounter_pk=id, payload=payload)


@router.get(
    "/{id}/diagnoses",
    response_model=list[DiagnosisResponse],
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider", "nurse", "viewer")),
    ],
    summary="List diagnoses for encounter",
)
async def get_diagnoses(
    id: uuid.UUID,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[DiagnosisResponse]:
    """Return all diagnoses attached to an encounter."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    return await svc.list_diagnoses(db=db, clinic_id=clinic_uuid, encounter_pk=id)


@router.put(
    "/{id}/diagnoses/{dx_id}",
    response_model=DiagnosisResponse,
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider")),
        Depends(audit_log),
    ],
    summary="Update diagnosis",
)
async def update_diagnosis_record(
    id: uuid.UUID,
    dx_id: uuid.UUID,
    payload: DiagnosisUpdate,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> DiagnosisResponse:
    """Update an existing diagnosis record."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    result = await svc.update_diagnosis(db=db, clinic_id=clinic_uuid, dx_id=dx_id, payload=payload)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnosis not found")
    return result


@router.delete(
    "/{id}/diagnoses/{dx_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider")),
        Depends(audit_log),
    ],
    summary="Remove diagnosis",
)
async def delete_diagnosis_record(
    id: uuid.UUID,
    dx_id: uuid.UUID,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a diagnosis from an encounter."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    if not await svc.delete_diagnosis(db=db, clinic_id=clinic_uuid, dx_id=dx_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnosis not found")


# ═════════════════════════════════════════════════════════════════════
#  Orders
# ═════════════════════════════════════════════════════════════════════

@router.post(
    "/{id}/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider")),
        Depends(audit_log),
    ],
    summary="Create order (lab/imaging/referral)",
)
async def add_order(
    id: uuid.UUID,
    payload: OrderCreate,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Create a clinical order (lab, imaging, medication, procedure, referral)."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    return await svc.create_order(db=db, clinic_id=clinic_uuid, encounter_pk=id, payload=payload)


@router.get(
    "/{id}/orders",
    response_model=list[OrderResponse],
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider", "nurse", "viewer")),
    ],
    summary="List orders with status",
)
async def get_orders(
    id: uuid.UUID,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[OrderResponse]:
    """Return all orders for an encounter."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    return await svc.list_orders(db=db, clinic_id=clinic_uuid, encounter_pk=id)


@router.patch(
    "/{id}/orders/{order_id}",
    response_model=OrderResponse,
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider", "nurse")),
        Depends(audit_log),
    ],
    summary="Update order status/result",
)
async def update_order_record(
    id: uuid.UUID,
    order_id: uuid.UUID,
    payload: OrderUpdate,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Update order status or attach a result summary."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    result = await svc.update_order(db=db, clinic_id=clinic_uuid, order_id=order_id, payload=payload)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return result


@router.delete(
    "/{id}/orders/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin")),
        Depends(audit_log),
    ],
    summary="Cancel/delete order",
)
async def delete_order_record(
    id: uuid.UUID,
    order_id: uuid.UUID,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete an order."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    if not await svc.delete_order(db=db, clinic_id=clinic_uuid, order_id=order_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")


# ═════════════════════════════════════════════════════════════════════
#  Prescriptions / Medications
# ═════════════════════════════════════════════════════════════════════

@router.post(
    "/{id}/medications",
    response_model=MedicationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider")),
        Depends(audit_log),
    ],
    summary="Add prescription",
)
async def add_medication(
    id: uuid.UUID,
    payload: MedicationCreate,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> MedicationResponse:
    """Prescribe a medication for the encounter."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    return await svc.create_medication(db=db, clinic_id=clinic_uuid, encounter_pk=id, payload=payload)


@router.get(
    "/{id}/medications",
    response_model=list[MedicationResponse],
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider", "nurse", "viewer")),
    ],
    summary="List prescriptions",
)
async def get_medications(
    id: uuid.UUID,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[MedicationResponse]:
    """Return all medications/prescriptions for an encounter."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    return await svc.list_medications(db=db, clinic_id=clinic_uuid, encounter_pk=id)


@router.put(
    "/{id}/medications/{med_id}",
    response_model=MedicationResponse,
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider")),
        Depends(audit_log),
    ],
    summary="Update prescription",
)
async def update_medication_record(
    id: uuid.UUID,
    med_id: uuid.UUID,
    payload: MedicationUpdate,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> MedicationResponse:
    """Update an existing prescription."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    result = await svc.update_medication(db=db, clinic_id=clinic_uuid, med_id=med_id, payload=payload)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication not found")
    return result


@router.delete(
    "/{id}/medications/{med_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider")),
        Depends(audit_log),
    ],
    summary="Cancel prescription",
)
async def delete_medication_record(
    id: uuid.UUID,
    med_id: uuid.UUID,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete (cancel) a prescription."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    if not await svc.delete_medication(db=db, clinic_id=clinic_uuid, med_id=med_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication not found")


# ═════════════════════════════════════════════════════════════════════
#  Disposition
# ═════════════════════════════════════════════════════════════════════

@router.post(
    "/{id}/disposition",
    response_model=DispositionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider")),
        Depends(audit_log),
    ],
    summary="Create discharge/disposition",
)
async def add_disposition(
    id: uuid.UUID,
    payload: DispositionCreate,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> DispositionResponse:
    """Create a disposition record (discharge, admit, refer, etc.)."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    return await svc.create_disposition(db=db, clinic_id=clinic_uuid, encounter_pk=id, payload=payload)


@router.get(
    "/{id}/disposition",
    response_model=DispositionResponse | None,
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider", "nurse", "viewer")),
    ],
    summary="Get disposition details",
)
async def get_disposition_record(
    id: uuid.UUID,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> DispositionResponse | None:
    """Return the disposition for an encounter, or null if none exists."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    return await svc.get_disposition(db=db, clinic_id=clinic_uuid, encounter_pk=id)


@router.put(
    "/{id}/disposition/{disp_id}",
    response_model=DispositionResponse,
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin", "provider")),
        Depends(audit_log),
    ],
    summary="Update disposition",
)
async def update_disposition_record(
    id: uuid.UUID,
    disp_id: uuid.UUID,
    payload: DispositionUpdate,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> DispositionResponse:
    """Update the disposition record."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    result = await svc.update_disposition(db=db, clinic_id=clinic_uuid, disp_id=disp_id, payload=payload)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disposition not found")
    return result


@router.delete(
    "/{id}/disposition/{disp_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(validate_encounter_exists),
        Depends(authorize_role("admin")),
        Depends(audit_log),
    ],
    summary="Delete disposition",
)
async def delete_disposition_record(
    id: uuid.UUID,
    disp_id: uuid.UUID,
    clinic_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a disposition record."""
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    if not await svc.delete_disposition(db=db, clinic_id=clinic_uuid, disp_id=disp_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disposition not found")
