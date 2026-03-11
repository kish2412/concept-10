"""Unit tests for encounter service methods (mock DB)."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.schemas.encounter import (
    DiagnosisCreate,
    DispositionCreate,
    EncounterCreate,
    EncounterUpdate,
    MedicationCreate,
    NoteCreate,
    NoteUpdate,
    OrderCreate,
    OrderUpdate,
    StatusUpdate,
    VitalsCreate,
)
from app.services import encounter_service as svc
from tests.factories import (
    CLINIC_ID,
    create_mock_diagnosis,
    create_mock_encounter,
    create_mock_medication,
    create_mock_note,
    create_mock_order,
    create_mock_vitals,
)

CLINIC_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
PATIENT_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
PROVIDER_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")

pytestmark = pytest.mark.asyncio


# ═══════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════

class TestHelpers:
    def test_generate_encounter_id_format(self):
        enc_id = svc._generate_encounter_id()
        assert enc_id.startswith("ENC-")
        parts = enc_id.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 4  # random hex

    def test_generate_encounter_id_unique(self):
        ids = {svc._generate_encounter_id() for _ in range(100)}
        assert len(ids) == 100

    def test_compute_bmi_valid(self):
        assert svc._compute_bmi(70.0, 170.0) == 24.22

    def test_compute_bmi_none_weight(self):
        assert svc._compute_bmi(None, 170.0) is None

    def test_compute_bmi_none_height(self):
        assert svc._compute_bmi(70.0, None) is None

    def test_compute_bmi_zero_height(self):
        assert svc._compute_bmi(70.0, 0.0) is None


# ═══════════════════════════════════════════════════════════════
#  Encounter CRUD
# ═══════════════════════════════════════════════════════════════

class TestCreateEncounter:
    async def test_creates_and_commits(self, mock_db: AsyncMock):
        payload = EncounterCreate(
            patient_id=PATIENT_ID,
            provider_id=PROVIDER_ID,
            encounter_type="CONSULTATION",
            chief_complaint="Headache",
        )
        result = await svc.create_encounter(db=mock_db, clinic_id=CLINIC_ID, payload=payload)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()
        assert result.clinic_id == CLINIC_ID
        assert result.encounter_id.startswith("ENC-")

    async def test_sets_default_status(self, mock_db: AsyncMock):
        payload = EncounterCreate(patient_id=PATIENT_ID)
        result = await svc.create_encounter(db=mock_db, clinic_id=CLINIC_ID, payload=payload)
        assert result.status == "SCHEDULED"


class TestGetEncounterById:
    async def test_returns_encounter(self, mock_db: AsyncMock):
        enc = create_mock_encounter()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = enc
        mock_db.execute.return_value = mock_result

        result = await svc.get_encounter_by_id(
            db=mock_db, clinic_id=CLINIC_ID, encounter_id=enc.id,
        )
        assert result is enc

    async def test_returns_none_when_not_found(self, mock_db: AsyncMock):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await svc.get_encounter_by_id(
            db=mock_db, clinic_id=CLINIC_ID, encounter_id=uuid.uuid4(),
        )
        assert result is None


class TestUpdateEncounter:
    async def test_updates_fields(self, mock_db: AsyncMock):
        enc = create_mock_encounter()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = enc
        mock_db.execute.return_value = mock_result

        payload = EncounterUpdate(chief_complaint="Updated complaint")
        result = await svc.update_encounter(
            db=mock_db, clinic_id=CLINIC_ID, encounter_id=enc.id, payload=payload,
        )
        assert result.chief_complaint == "Updated complaint"
        mock_db.commit.assert_awaited()

    async def test_returns_none_when_missing(self, mock_db: AsyncMock):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        payload = EncounterUpdate(chief_complaint="test")
        result = await svc.update_encounter(
            db=mock_db, clinic_id=CLINIC_ID, encounter_id=uuid.uuid4(), payload=payload,
        )
        assert result is None


class TestSoftDeleteEncounter:
    async def test_marks_deleted(self, mock_db: AsyncMock):
        enc = create_mock_encounter()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = enc
        mock_db.execute.return_value = mock_result

        result = await svc.soft_delete_encounter(
            db=mock_db, clinic_id=CLINIC_ID, encounter_id=enc.id,
        )
        assert result is True
        assert enc.is_deleted is True
        assert enc.deleted_at is not None

    async def test_returns_false_when_missing(self, mock_db: AsyncMock):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await svc.soft_delete_encounter(
            db=mock_db, clinic_id=CLINIC_ID, encounter_id=uuid.uuid4(),
        )
        assert result is False


class TestUpdateEncounterStatus:
    async def test_updates_status(self, mock_db: AsyncMock):
        enc = create_mock_encounter(status="SCHEDULED")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = enc
        mock_db.execute.return_value = mock_result

        payload = StatusUpdate(
            status="WITH_PROVIDER",
            triage_assessment={
                "acuity": "URGENT",
                "presenting_symptoms": ["headache"],
                "symptom_onset": "2 days",
                "pain_score": 6,
                "red_flags": [],
                "isolation_required": False,
                "mobility_status": "ambulatory",
                "allergies_verified": True,
                "triage_notes": "Needs provider review after vitals and symptom screening.",
            },
        )
        result = await svc.update_encounter_status(
            db=mock_db, clinic_id=CLINIC_ID, encounter_id=enc.id, payload=payload,
        )
        assert result.status == "WITH_PROVIDER"
        assert result.triage_assessment is not None

    async def test_requires_triage_assessment_for_with_provider(self, mock_db: AsyncMock):
        enc = create_mock_encounter(status="TRIAGE", triage_assessment=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = enc
        mock_db.execute.return_value = mock_result

        payload = StatusUpdate(status="WITH_PROVIDER")

        with pytest.raises(svc.EncounterStatusTransitionError):
            await svc.update_encounter_status(
                db=mock_db, clinic_id=CLINIC_ID, encounter_id=enc.id, payload=payload,
            )

    async def test_returns_none_when_missing(self, mock_db: AsyncMock):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        payload = StatusUpdate(status="WITH_PROVIDER")
        result = await svc.update_encounter_status(
            db=mock_db, clinic_id=CLINIC_ID, encounter_id=uuid.uuid4(), payload=payload,
        )
        assert result is None


# ═══════════════════════════════════════════════════════════════
#  Vitals CRUD
# ═══════════════════════════════════════════════════════════════

class TestVitals:
    async def test_create_vitals_computes_bmi(self, mock_db: AsyncMock):
        payload = VitalsCreate(
            blood_pressure_systolic=120,
            blood_pressure_diastolic=80,
            weight=70.0,
            height=170.0,
        )
        result = await svc.create_vitals(
            db=mock_db, clinic_id=CLINIC_ID, encounter_pk=uuid.uuid4(), payload=payload,
        )
        assert result.bmi == 24.22
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    async def test_create_vitals_none_bmi_when_missing_data(self, mock_db: AsyncMock):
        payload = VitalsCreate(blood_pressure_systolic=120)
        result = await svc.create_vitals(
            db=mock_db, clinic_id=CLINIC_ID, encounter_pk=uuid.uuid4(), payload=payload,
        )
        assert result.bmi is None

    async def test_update_vitals_not_found(self, mock_db: AsyncMock):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        from app.schemas.encounter import VitalsUpdate
        result = await svc.update_vitals(
            db=mock_db, clinic_id=CLINIC_ID, vitals_id=uuid.uuid4(),
            payload=VitalsUpdate(pulse_rate=80),
        )
        assert result is None

    async def test_delete_vitals_marks_deleted(self, mock_db: AsyncMock):
        vitals = create_mock_vitals()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = vitals
        mock_db.execute.return_value = mock_result

        result = await svc.delete_vitals(
            db=mock_db, clinic_id=CLINIC_ID, vitals_id=vitals.id,
        )
        assert result is True
        assert vitals.is_deleted is True


# ═══════════════════════════════════════════════════════════════
#  Notes CRUD
# ═══════════════════════════════════════════════════════════════

class TestNotes:
    async def test_create_note(self, mock_db: AsyncMock):
        payload = NoteCreate(
            note_type="SOAP",
            subjective="Headache for 3 days",
            assessment="Tension headache",
        )
        result = await svc.create_note(
            db=mock_db, clinic_id=CLINIC_ID, encounter_pk=uuid.uuid4(), payload=payload,
        )
        assert result.note_type == "SOAP"
        mock_db.add.assert_called_once()

    async def test_update_note_bumps_version(self, mock_db: AsyncMock):
        note = create_mock_note(version=1)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = note
        mock_db.execute.return_value = mock_result

        payload = NoteUpdate(subjective="Updated subjective")
        result = await svc.update_note(
            db=mock_db, clinic_id=CLINIC_ID, note_id=note.id, payload=payload,
        )
        assert result.version == 2

    async def test_update_note_not_found(self, mock_db: AsyncMock):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        payload = NoteUpdate(subjective="test")
        result = await svc.update_note(
            db=mock_db, clinic_id=CLINIC_ID, note_id=uuid.uuid4(), payload=payload,
        )
        assert result is None


class TestSignNote:
    async def test_signs_note(self, mock_db: AsyncMock):
        note = create_mock_note(is_signed=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = note
        mock_db.execute.return_value = mock_result

        result = await svc.sign_note(
            db=mock_db, clinic_id=CLINIC_ID, note_id=note.id,
        )
        assert result.is_signed is True
        assert result.signed_at is not None

    async def test_sign_already_signed_is_noop(self, mock_db: AsyncMock):
        signed_at = datetime.now(timezone.utc)
        note = create_mock_note(is_signed=True, signed_at=signed_at)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = note
        mock_db.execute.return_value = mock_result

        result = await svc.sign_note(
            db=mock_db, clinic_id=CLINIC_ID, note_id=note.id,
        )
        assert result.is_signed is True
        assert result.signed_at == signed_at  # unchanged

    async def test_sign_not_found(self, mock_db: AsyncMock):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await svc.sign_note(
            db=mock_db, clinic_id=CLINIC_ID, note_id=uuid.uuid4(),
        )
        assert result is None


# ═══════════════════════════════════════════════════════════════
#  Diagnosis CRUD
# ═══════════════════════════════════════════════════════════════

class TestDiagnosis:
    async def test_create_diagnosis(self, mock_db: AsyncMock):
        payload = DiagnosisCreate(
            icd_code="J06.9",
            icd_description="Acute upper respiratory infection",
        )
        result = await svc.create_diagnosis(
            db=mock_db, clinic_id=CLINIC_ID, encounter_pk=uuid.uuid4(), payload=payload,
        )
        assert result.icd_code == "J06.9"
        mock_db.add.assert_called_once()

    async def test_delete_diagnosis_marks_deleted(self, mock_db: AsyncMock):
        dx = create_mock_diagnosis()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = dx
        mock_db.execute.return_value = mock_result

        result = await svc.delete_diagnosis(db=mock_db, clinic_id=CLINIC_ID, dx_id=dx.id)
        assert result is True
        assert dx.is_deleted is True

    async def test_delete_diagnosis_not_found(self, mock_db: AsyncMock):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await svc.delete_diagnosis(
            db=mock_db, clinic_id=CLINIC_ID, dx_id=uuid.uuid4(),
        )
        assert result is False


# ═══════════════════════════════════════════════════════════════
#  Order CRUD
# ═══════════════════════════════════════════════════════════════

class TestOrder:
    async def test_create_order(self, mock_db: AsyncMock):
        payload = OrderCreate(
            order_type="LAB",
            order_description="CBC with differential",
            priority="URGENT",
        )
        result = await svc.create_order(
            db=mock_db, clinic_id=CLINIC_ID, encounter_pk=uuid.uuid4(), payload=payload,
        )
        assert result.order_type == "LAB"
        assert result.priority == "URGENT"
        mock_db.add.assert_called_once()

    async def test_update_order_status(self, mock_db: AsyncMock):
        order = create_mock_order(status="PENDING")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = order
        mock_db.execute.return_value = mock_result

        payload = OrderUpdate(status="RESULTED", result_summary="Normal values")
        result = await svc.update_order(
            db=mock_db, clinic_id=CLINIC_ID, order_id=order.id, payload=payload,
        )
        assert result.status == "RESULTED"
        assert result.result_summary == "Normal values"

    async def test_delete_order(self, mock_db: AsyncMock):
        order = create_mock_order()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = order
        mock_db.execute.return_value = mock_result

        result = await svc.delete_order(db=mock_db, clinic_id=CLINIC_ID, order_id=order.id)
        assert result is True
        assert order.is_deleted is True


# ═══════════════════════════════════════════════════════════════
#  Medication CRUD
# ═══════════════════════════════════════════════════════════════

class TestMedication:
    async def test_create_medication(self, mock_db: AsyncMock):
        payload = MedicationCreate(
            drug_name="Ibuprofen",
            dosage="400",
            dosage_unit="mg",
            frequency="TID",
            route="PO",
        )
        result = await svc.create_medication(
            db=mock_db, clinic_id=CLINIC_ID, encounter_pk=uuid.uuid4(), payload=payload,
        )
        assert result.drug_name == "Ibuprofen"
        mock_db.add.assert_called_once()

    async def test_delete_medication(self, mock_db: AsyncMock):
        med = create_mock_medication()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = med
        mock_db.execute.return_value = mock_result

        result = await svc.delete_medication(db=mock_db, clinic_id=CLINIC_ID, med_id=med.id)
        assert result is True


# ═══════════════════════════════════════════════════════════════
#  Disposition CRUD
# ═══════════════════════════════════════════════════════════════

class TestDisposition:
    async def test_create_disposition(self, mock_db: AsyncMock):
        payload = DispositionCreate(
            disposition_type="DISCHARGE",
            follow_up_required=True,
            follow_up_in_days=7,
            discharge_instructions="Follow up in 1 week",
        )
        result = await svc.create_disposition(
            db=mock_db, clinic_id=CLINIC_ID, encounter_pk=uuid.uuid4(), payload=payload,
        )
        assert result.disposition_type == "DISCHARGE"
        assert result.follow_up_required is True
        mock_db.add.assert_called_once()
