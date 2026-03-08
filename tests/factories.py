"""
Factory functions for creating test fixtures across the encounter module.

Usage::

    from tests.factories import create_mock_encounter

    enc = create_mock_encounter(status="WITH_PROVIDER", chief_complaint="Headache")
"""

import uuid
from datetime import datetime, timezone

from app.models.encounter import (
    Encounter,
    EncounterDiagnosis,
    EncounterDisposition,
    EncounterMedication,
    EncounterNote,
    EncounterOrder,
    EncounterVitals,
)

_CLINIC_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_PATIENT_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_PROVIDER_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Core encounter ───────────────────────────────────────────────

def create_mock_encounter(**overrides) -> Encounter:
    """Return a fully populated ``Encounter`` ORM object with nested relations."""
    defaults = dict(
        id=uuid.uuid4(),
        clinic_id=_CLINIC_ID,
        encounter_id="ENC-20260307-ABCD",
        patient_id=_PATIENT_ID,
        provider_id=_PROVIDER_ID,
        facility_id=None,
        department_id=None,
        encounter_type="CONSULTATION",
        status="SCHEDULED",
        chief_complaint="Chest pain",
        ai_triage_summary=None,
        ai_triage_focus_points=None,
        ai_triage_red_flags=None,
        ai_triage_missing_information=None,
        ai_triage_generated_at=None,
        ai_triage_orchestration=None,
        ai_triage_model_provider=None,
        ai_triage_model_name=None,
        ai_triage_guardrail_profile=None,
        scheduled_at=_now(),
        checked_in_at=None,
        triage_at=None,
        started_at=None,
        ended_at=None,
        created_by=_PROVIDER_ID,
        updated_by=None,
        deleted_at=None,
        is_deleted=False,
        created_at=_now(),
        updated_at=_now(),
    )
    defaults.update(overrides)

    enc = Encounter.__new__(Encounter)
    for k, v in defaults.items():
        object.__setattr__(enc, k, v)

    # Attach default nested children unless explicitly overridden
    if "vitals" not in overrides:
        object.__setattr__(enc, "vitals", [create_mock_vitals(encounter_id=defaults["id"])])
    if "notes" not in overrides:
        object.__setattr__(enc, "notes", [create_mock_note(encounter_id=defaults["id"])])
    if "diagnoses" not in overrides:
        object.__setattr__(enc, "diagnoses", [create_mock_diagnosis(encounter_id=defaults["id"])])
    if "orders" not in overrides:
        object.__setattr__(enc, "orders", [create_mock_order(encounter_id=defaults["id"])])
    if "medications" not in overrides:
        object.__setattr__(enc, "medications", [create_mock_medication(encounter_id=defaults["id"])])
    if "disposition" not in overrides:
        object.__setattr__(enc, "disposition", None)
    if "patient" not in overrides:
        object.__setattr__(enc, "patient", None)

    return enc


# ── Sub-resources ────────────────────────────────────────────────

def create_mock_vitals(**overrides) -> EncounterVitals:
    defaults = dict(
        id=uuid.uuid4(),
        clinic_id=_CLINIC_ID,
        encounter_id=uuid.uuid4(),
        blood_pressure_systolic=120,
        blood_pressure_diastolic=80,
        pulse_rate=72.0,
        respiratory_rate=16.0,
        temperature=37.0,
        oxygen_saturation=98.0,
        weight=70.0,
        height=170.0,
        bmi=24.22,
        pain_score=3,
        recorded_by=_PROVIDER_ID,
        recorded_at=_now(),
        is_deleted=False,
        created_at=_now(),
        updated_at=_now(),
    )
    defaults.update(overrides)
    obj = EncounterVitals.__new__(EncounterVitals)
    for k, v in defaults.items():
        object.__setattr__(obj, k, v)
    return obj


def create_mock_note(**overrides) -> EncounterNote:
    defaults = dict(
        id=uuid.uuid4(),
        clinic_id=_CLINIC_ID,
        encounter_id=uuid.uuid4(),
        note_type="SOAP",
        subjective="Patient reports chest pain radiating to left arm",
        objective="BP 140/90, HR 88",
        assessment="Possible angina pectoris",
        plan="Order troponin, ECG. Consider cardiology consult.",
        author_id=_PROVIDER_ID,
        author_role="provider",
        is_signed=False,
        signed_at=None,
        version=1,
        is_deleted=False,
        created_at=_now(),
        updated_at=_now(),
    )
    defaults.update(overrides)
    obj = EncounterNote.__new__(EncounterNote)
    for k, v in defaults.items():
        object.__setattr__(obj, k, v)
    return obj


def create_mock_diagnosis(**overrides) -> EncounterDiagnosis:
    defaults = dict(
        id=uuid.uuid4(),
        clinic_id=_CLINIC_ID,
        encounter_id=uuid.uuid4(),
        icd_code="I20.9",
        icd_description="Angina pectoris, unspecified",
        diagnosis_type="PRIMARY",
        onset_date=None,
        is_chronic_condition=False,
        added_by=_PROVIDER_ID,
        is_deleted=False,
        created_at=_now(),
        updated_at=_now(),
    )
    defaults.update(overrides)
    obj = EncounterDiagnosis.__new__(EncounterDiagnosis)
    for k, v in defaults.items():
        object.__setattr__(obj, k, v)
    return obj


def create_mock_order(**overrides) -> EncounterOrder:
    defaults = dict(
        id=uuid.uuid4(),
        clinic_id=_CLINIC_ID,
        encounter_id=uuid.uuid4(),
        order_type="LAB",
        order_code="TROP-I",
        order_description="Troponin I",
        status="PENDING",
        priority="STAT",
        ordered_by=_PROVIDER_ID,
        ordered_at=_now(),
        result_summary=None,
        is_deleted=False,
        created_at=_now(),
        updated_at=_now(),
    )
    defaults.update(overrides)
    obj = EncounterOrder.__new__(EncounterOrder)
    for k, v in defaults.items():
        object.__setattr__(obj, k, v)
    return obj


def create_mock_medication(**overrides) -> EncounterMedication:
    defaults = dict(
        id=uuid.uuid4(),
        clinic_id=_CLINIC_ID,
        encounter_id=uuid.uuid4(),
        drug_code="NDC-12345",
        drug_name="Aspirin",
        generic_name="Acetylsalicylic acid",
        dosage="81",
        dosage_unit="mg",
        frequency="QD",
        route="PO",
        duration_days=30,
        quantity=30,
        special_instructions="Take with food",
        is_controlled_substance=False,
        prescribed_by=_PROVIDER_ID,
        prescribed_at=_now(),
        is_deleted=False,
        created_at=_now(),
        updated_at=_now(),
    )
    defaults.update(overrides)
    obj = EncounterMedication.__new__(EncounterMedication)
    for k, v in defaults.items():
        object.__setattr__(obj, k, v)
    return obj


def create_mock_disposition(**overrides) -> EncounterDisposition:
    defaults = dict(
        id=uuid.uuid4(),
        clinic_id=_CLINIC_ID,
        encounter_id=uuid.uuid4(),
        disposition_type="DISCHARGE",
        follow_up_required=True,
        follow_up_in_days=7,
        discharge_instructions="Rest, avoid strenuous activity",
        activity_restrictions="No heavy lifting for 2 weeks",
        diet_instructions="Low sodium diet",
        patient_education_materials=["heart-health-101"],
        discharged_by=_PROVIDER_ID,
        discharged_at=_now(),
        is_deleted=False,
        created_at=_now(),
        updated_at=_now(),
    )
    defaults.update(overrides)
    obj = EncounterDisposition.__new__(EncounterDisposition)
    for k, v in defaults.items():
        object.__setattr__(obj, k, v)
    return obj


# ── Frontend-compatible dict ─────────────────────────────────────

def create_mock_encounter_dict(**overrides) -> dict:
    """Return a plain dict matching the EncounterResponse JSON shape."""
    enc_id = overrides.pop("id", str(uuid.uuid4()))
    defaults = dict(
        id=enc_id,
        clinic_id=str(_CLINIC_ID),
        encounter_id="ENC-20260307-ABCD",
        patient_id=str(_PATIENT_ID),
        provider_id=str(_PROVIDER_ID),
        facility_id=None,
        department_id=None,
        encounter_type="CONSULTATION",
        status="SCHEDULED",
        chief_complaint="Chest pain",
        ai_triage_summary=None,
        ai_triage_focus_points=None,
        ai_triage_red_flags=None,
        ai_triage_missing_information=None,
        ai_triage_generated_at=None,
        ai_triage_orchestration=None,
        ai_triage_model_provider=None,
        ai_triage_model_name=None,
        ai_triage_guardrail_profile=None,
        scheduled_at=_now().isoformat(),
        checked_in_at=None,
        triage_at=None,
        started_at=None,
        ended_at=None,
        created_by=str(_PROVIDER_ID),
        updated_by=None,
        deleted_at=None,
        created_at=_now().isoformat(),
        updated_at=_now().isoformat(),
        is_deleted=False,
        patient={"id": str(_PATIENT_ID), "first_name": "Jane", "last_name": "Doe"},
        vitals=[],
        notes=[],
        diagnoses=[],
        orders=[],
        medications=[],
        disposition=None,
    )
    defaults.update(overrides)
    return defaults
