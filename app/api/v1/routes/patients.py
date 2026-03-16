import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clinic_id
from app.core.database import get_db
from app.schemas.patient_background import PatientBackgroundResponse, PatientBackgroundUpdate
from app.schemas.patient import PatientCreate, PatientListResponse, PatientResponse, PatientUpdate
from app.services.patient_background_service import get_or_create_patient_background, update_patient_background
from app.services.patient_service import (
    create_patient,
    get_patient_by_id,
    list_patients,
    soft_delete_patient,
    update_patient,
)

router = APIRouter()


def _parse_clinic_uuid(clinic_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(clinic_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant context") from exc


@router.get("", response_model=PatientListResponse)
async def get_patients(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    clinic_id: str = Depends(get_clinic_id),
    db: AsyncSession = Depends(get_db),
) -> PatientListResponse:
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    items, total = await list_patients(db=db, clinic_id=clinic_uuid, page=page, size=size, search=search)
    return PatientListResponse(items=items, page=page, size=size, total=total)


@router.get("/{id}", response_model=PatientResponse)
async def get_patient(
    id: uuid.UUID,
    clinic_id: str = Depends(get_clinic_id),
    db: AsyncSession = Depends(get_db),
) -> PatientResponse:
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    patient = await get_patient_by_id(db=db, clinic_id=clinic_uuid, patient_id=id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient_record(
    payload: PatientCreate,
    clinic_id: str = Depends(get_clinic_id),
    db: AsyncSession = Depends(get_db),
) -> PatientResponse:
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    return await create_patient(db=db, clinic_id=clinic_uuid, payload=payload)


@router.put("/{id}", response_model=PatientResponse)
async def update_patient_record(
    id: uuid.UUID,
    payload: PatientUpdate,
    clinic_id: str = Depends(get_clinic_id),
    db: AsyncSession = Depends(get_db),
) -> PatientResponse:
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    patient = await update_patient(db=db, clinic_id=clinic_uuid, patient_id=id, payload=payload)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient_record(
    id: uuid.UUID,
    clinic_id: str = Depends(get_clinic_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    deleted = await soft_delete_patient(db=db, clinic_id=clinic_uuid, patient_id=id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")


@router.get("/{id}/background", response_model=PatientBackgroundResponse)
async def get_patient_background_record(
    id: uuid.UUID,
    clinic_id: str = Depends(get_clinic_id),
    db: AsyncSession = Depends(get_db),
) -> PatientBackgroundResponse:
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    background = await get_or_create_patient_background(db=db, clinic_id=clinic_uuid, patient_id=id)
    if not background:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return background


@router.put("/{id}/background", response_model=PatientBackgroundResponse)
async def update_patient_background_record(
    id: uuid.UUID,
    payload: PatientBackgroundUpdate,
    clinic_id: str = Depends(get_clinic_id),
    db: AsyncSession = Depends(get_db),
) -> PatientBackgroundResponse:
    clinic_uuid = _parse_clinic_uuid(clinic_id)
    background = await update_patient_background(db=db, clinic_id=clinic_uuid, patient_id=id, payload=payload)
    if not background:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return background
