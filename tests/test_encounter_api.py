"""Integration tests for encounter API endpoints.

Tests hit the real FastAPI app (with mocked DB) via httpx AsyncClient.
Coverage:
  - Happy path: valid input, correct role → 200/201
  - Auth guard: missing auth state → 401
  - RBAC: wrong role → 403
  - Validation: bad payload → 422
  - Not found: invalid encounter ID → 404
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.services import encounter_service as encounter_svc
from tests.factories import (
    create_mock_disposition,
    create_mock_encounter,
    create_mock_medication,
    create_mock_note,
    create_mock_order,
    create_mock_vitals,
)

pytestmark = pytest.mark.asyncio

ENC_ID = uuid.uuid4()
API = "/api/v1/encounters"

# Common patch target prefix (routes import ``encounter_service as svc``)
_SVC = "app.services.encounter_service"


# ═══════════════════════════════════════════════════════════════
#  POST / — Create encounter
# ═══════════════════════════════════════════════════════════════

class TestCreateEncounterEndpoint:
    async def test_happy_path_201(self, client_provider: AsyncClient):
        enc = create_mock_encounter(id=ENC_ID)
        with patch(
            "app.services.encounter_service.create_encounter",
            new_callable=AsyncMock,
            return_value=enc,
        ):
            resp = await client_provider.post(API, json={
                "patient_id": str(uuid.uuid4()),
                "encounter_type": "CONSULTATION",
                "chief_complaint": "Headache",
            })
        assert resp.status_code == 201
        data = resp.json()
        assert data["encounter_id"].startswith("ENC-")

    async def test_viewer_forbidden_403(self, client_viewer: AsyncClient):
        resp = await client_viewer.post(API, json={
            "patient_id": str(uuid.uuid4()),
        })
        assert resp.status_code == 403

    async def test_missing_patient_id_422(self, client_provider: AsyncClient):
        resp = await client_provider.post(API, json={
            "encounter_type": "CONSULTATION",
        })
        assert resp.status_code == 422

    async def test_invalid_encounter_type_422(self, client_provider: AsyncClient):
        resp = await client_provider.post(API, json={
            "patient_id": str(uuid.uuid4()),
            "encounter_type": "INVALID_TYPE",
        })
        assert resp.status_code == 422

    async def test_no_auth_401(self, client_no_auth: AsyncClient):
        resp = await client_no_auth.post(API, json={
            "patient_id": str(uuid.uuid4()),
        })
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════
#  GET /{id} — Get encounter detail
# ═══════════════════════════════════════════════════════════════

class TestGetEncounterEndpoint:
    async def test_happy_path_200(self, client_provider: AsyncClient):
        enc = create_mock_encounter(id=ENC_ID)
        with patch(
            "app.services.encounter_service.get_encounter_by_id",
            new_callable=AsyncMock,
            return_value=enc,
        ):
            resp = await client_provider.get(f"{API}/{ENC_ID}")
        assert resp.status_code == 200
        assert resp.json()["id"] == str(ENC_ID)

    async def test_not_found_404(self, client_provider: AsyncClient):
        with patch(
            "app.services.encounter_service.get_encounter_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client_provider.get(f"{API}/{uuid.uuid4()}")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    async def test_invalid_uuid_422(self, client_provider: AsyncClient):
        resp = await client_provider.get(f"{API}/not-a-uuid")
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════
#  PATCH /{id}/status — Status transition
# ═══════════════════════════════════════════════════════════════

class TestUpdateStatusEndpoint:
    async def test_happy_path_200(self, client_provider: AsyncClient):
        enc = create_mock_encounter(id=ENC_ID, status="WITH_PROVIDER")
        with patch(
            "app.services.encounter_service.update_encounter_status",
            new_callable=AsyncMock,
            return_value=enc,
        ):
            resp = await client_provider.patch(f"{API}/{ENC_ID}/status", json={
                "status": "WITH_PROVIDER",
                "triage_assessment": {
                    "acuity": "URGENT",
                    "presenting_symptoms": ["headache"],
                    "symptom_onset": "today",
                    "pain_score": 5,
                    "red_flags": [],
                    "isolation_required": False,
                    "mobility_status": "ambulatory",
                    "allergies_verified": True,
                    "triage_notes": "Patient stable but requires provider assessment.",
                },
            })
        assert resp.status_code == 200
        assert resp.json()["status"] == "WITH_PROVIDER"

    async def test_invalid_status_422(self, client_provider: AsyncClient):
        resp = await client_provider.patch(f"{API}/{ENC_ID}/status", json={
            "status": "NONEXISTENT",
        })
        assert resp.status_code == 422

    async def test_viewer_forbidden_403(self, client_viewer: AsyncClient):
        resp = await client_viewer.patch(f"{API}/{ENC_ID}/status", json={
            "status": "WITH_PROVIDER",
        })
        assert resp.status_code == 403

    async def test_not_found_404(self, client_provider: AsyncClient):
        with patch(
            "app.services.encounter_service.update_encounter_status",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client_provider.patch(f"{API}/{uuid.uuid4()}/status", json={
                "status": "WITH_PROVIDER",
            })
        assert resp.status_code == 404

    async def test_triage_requirement_error_400(self, client_provider: AsyncClient):
        with patch(
            "app.services.encounter_service.update_encounter_status",
            new_callable=AsyncMock,
            side_effect=encounter_svc.EncounterStatusTransitionError(
                "Detailed triage assessment is required before entering in-consultation."
            ),
        ):
            resp = await client_provider.patch(f"{API}/{ENC_ID}/status", json={
                "status": "WITH_PROVIDER",
            })

        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════
#  DELETE /{id} — Soft delete (admin only)
# ═══════════════════════════════════════════════════════════════

class TestDeleteEncounterEndpoint:
    async def test_admin_can_delete_204(self, client_admin: AsyncClient):
        with patch(
            "app.services.encounter_service.soft_delete_encounter",
            new_callable=AsyncMock,
            return_value=True,
        ):
            resp = await client_admin.delete(f"{API}/{ENC_ID}")
        assert resp.status_code == 204

    async def test_provider_forbidden_403(self, client_provider: AsyncClient):
        resp = await client_provider.delete(f"{API}/{ENC_ID}")
        assert resp.status_code == 403

    async def test_viewer_forbidden_403(self, client_viewer: AsyncClient):
        resp = await client_viewer.delete(f"{API}/{ENC_ID}")
        assert resp.status_code == 403

    async def test_not_found_404(self, client_admin: AsyncClient):
        with patch(
            "app.services.encounter_service.soft_delete_encounter",
            new_callable=AsyncMock,
            return_value=False,
        ):
            resp = await client_admin.delete(f"{API}/{uuid.uuid4()}")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════
#  GET /queue — Live encounter queue
# ═══════════════════════════════════════════════════════════════

class TestQueueEndpoint:
    async def test_happy_path_200(self, client_provider: AsyncClient):
        enc = create_mock_encounter()
        with patch(
            "app.services.encounter_service.get_encounter_queue",
            new_callable=AsyncMock,
            return_value=([enc], 1),
        ):
            resp = await client_provider.get(f"{API}/queue")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    async def test_viewer_can_read_200(self, client_viewer: AsyncClient):
        with patch(
            "app.services.encounter_service.get_encounter_queue",
            new_callable=AsyncMock,
            return_value=([], 0),
        ):
            resp = await client_viewer.get(f"{API}/queue")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════
#  GET /today — Summary
# ═══════════════════════════════════════════════════════════════

class TestTodaySummaryEndpoint:
    async def test_happy_path_200(self, client_provider: AsyncClient):
        with patch(
            "app.services.encounter_service.get_today_summary",
            new_callable=AsyncMock,
            return_value={"total": 5, "by_status": {"SCHEDULED": 3, "WITH_PROVIDER": 2}, "by_type": {"CONSULTATION": 5}},
        ):
            resp = await client_provider.get(f"{API}/today")
        assert resp.status_code == 200
        assert resp.json()["total"] == 5


# ═══════════════════════════════════════════════════════════════
#  POST /{id}/notes — Add note
# ═══════════════════════════════════════════════════════════════

class TestNotesEndpoint:
    async def test_create_note_201(self, client_provider: AsyncClient):
        note = create_mock_note()
        with (
            patch(
                "app.services.encounter_service.get_encounter_by_id",
                new_callable=AsyncMock,
                return_value=create_mock_encounter(id=ENC_ID),
            ),
            patch(
                "app.services.encounter_service.create_note",
                new_callable=AsyncMock,
                return_value=note,
            ),
        ):
            resp = await client_provider.post(f"{API}/{ENC_ID}/notes", json={
                "note_type": "SOAP",
                "subjective": "Patient reports headache",
            })
        assert resp.status_code == 201

    async def test_viewer_cannot_create_403(self, client_viewer: AsyncClient):
        with patch(
            "app.services.encounter_service.get_encounter_by_id",
            new_callable=AsyncMock,
            return_value=create_mock_encounter(id=ENC_ID),
        ):
            resp = await client_viewer.post(f"{API}/{ENC_ID}/notes", json={
                "note_type": "SOAP",
                "subjective": "test",
            })
        assert resp.status_code == 403


class TestSignNoteEndpoint:
    async def test_sign_note_200(self, client_provider: AsyncClient):
        note = create_mock_note(is_signed=True)
        with (
            patch(
                "app.services.encounter_service.get_encounter_by_id",
                new_callable=AsyncMock,
                return_value=create_mock_encounter(id=ENC_ID),
            ),
            patch(
                "app.services.encounter_service.sign_note",
                new_callable=AsyncMock,
                return_value=note,
            ),
        ):
            resp = await client_provider.post(f"{API}/{ENC_ID}/notes/{note.id}/sign")
        assert resp.status_code == 200
        assert resp.json()["is_signed"] is True

    async def test_sign_note_not_found_404(self, client_provider: AsyncClient):
        with (
            patch(
                "app.services.encounter_service.get_encounter_by_id",
                new_callable=AsyncMock,
                return_value=create_mock_encounter(id=ENC_ID),
            ),
            patch(
                "app.services.encounter_service.sign_note",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            resp = await client_provider.post(f"{API}/{ENC_ID}/notes/{uuid.uuid4()}/sign")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════
#  POST /{id}/orders — Add order
# ═══════════════════════════════════════════════════════════════

class TestOrdersEndpoint:
    async def test_create_order_201(self, client_provider: AsyncClient):
        order = create_mock_order()
        with (
            patch(
                "app.services.encounter_service.get_encounter_by_id",
                new_callable=AsyncMock,
                return_value=create_mock_encounter(id=ENC_ID),
            ),
            patch(
                "app.services.encounter_service.create_order",
                new_callable=AsyncMock,
                return_value=order,
            ),
        ):
            resp = await client_provider.post(f"{API}/{ENC_ID}/orders", json={
                "order_type": "LAB",
                "order_description": "CBC",
            })
        assert resp.status_code == 201

    async def test_viewer_cannot_create_403(self, client_viewer: AsyncClient):
        with patch(
            "app.services.encounter_service.get_encounter_by_id",
            new_callable=AsyncMock,
            return_value=create_mock_encounter(id=ENC_ID),
        ):
            resp = await client_viewer.post(f"{API}/{ENC_ID}/orders", json={
                "order_type": "LAB",
                "order_description": "CBC",
            })
        assert resp.status_code == 403

    async def test_invalid_order_type_422(self, client_provider: AsyncClient):
        with patch(
            "app.services.encounter_service.get_encounter_by_id",
            new_callable=AsyncMock,
            return_value=create_mock_encounter(id=ENC_ID),
        ):
            resp = await client_provider.post(f"{API}/{ENC_ID}/orders", json={
                "order_type": "INVALID",
                "order_description": "CBC",
            })
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════
#  POST /{id}/medications — Add prescription
# ═══════════════════════════════════════════════════════════════

class TestMedicationsEndpoint:
    async def test_create_medication_201(self, client_provider: AsyncClient):
        med = create_mock_medication()
        with (
            patch(
                "app.services.encounter_service.get_encounter_by_id",
                new_callable=AsyncMock,
                return_value=create_mock_encounter(id=ENC_ID),
            ),
            patch(
                "app.services.encounter_service.create_medication",
                new_callable=AsyncMock,
                return_value=med,
            ),
        ):
            resp = await client_provider.post(f"{API}/{ENC_ID}/medications", json={
                "drug_name": "Aspirin",
                "dosage": "81",
                "dosage_unit": "mg",
                "frequency": "QD",
                "route": "PO",
            })
        assert resp.status_code == 201

    async def test_missing_required_fields_422(self, client_provider: AsyncClient):
        with patch(
            "app.services.encounter_service.get_encounter_by_id",
            new_callable=AsyncMock,
            return_value=create_mock_encounter(id=ENC_ID),
        ):
            resp = await client_provider.post(f"{API}/{ENC_ID}/medications", json={
                "drug_name": "Aspirin",
                # missing dosage, dosage_unit, frequency, route
            })
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════
#  POST /{id}/disposition — Create disposition
# ═══════════════════════════════════════════════════════════════

class TestDispositionEndpoint:
    async def test_create_disposition_201(self, client_provider: AsyncClient):
        disp = create_mock_disposition()
        with (
            patch(
                "app.services.encounter_service.get_encounter_by_id",
                new_callable=AsyncMock,
                return_value=create_mock_encounter(id=ENC_ID),
            ),
            patch(
                "app.services.encounter_service.create_disposition",
                new_callable=AsyncMock,
                return_value=disp,
            ),
        ):
            resp = await client_provider.post(f"{API}/{ENC_ID}/disposition", json={
                "disposition_type": "DISCHARGE",
                "follow_up_required": True,
                "follow_up_in_days": 7,
            })
        assert resp.status_code == 201

    async def test_invalid_disposition_type_422(self, client_provider: AsyncClient):
        with patch(
            "app.services.encounter_service.get_encounter_by_id",
            new_callable=AsyncMock,
            return_value=create_mock_encounter(id=ENC_ID),
        ):
            resp = await client_provider.post(f"{API}/{ENC_ID}/disposition", json={
                "disposition_type": "INVALID_TYPE",
            })
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════
#  POST /{id}/vitals — Add vitals
# ═══════════════════════════════════════════════════════════════

class TestVitalsEndpoint:
    async def test_create_vitals_201(self, client_provider: AsyncClient):
        vitals = create_mock_vitals()
        with (
            patch(
                "app.services.encounter_service.get_encounter_by_id",
                new_callable=AsyncMock,
                return_value=create_mock_encounter(id=ENC_ID),
            ),
            patch(
                "app.services.encounter_service.create_vitals",
                new_callable=AsyncMock,
                return_value=vitals,
            ),
        ):
            resp = await client_provider.post(f"{API}/{ENC_ID}/vitals", json={
                "blood_pressure_systolic": 120,
                "blood_pressure_diastolic": 80,
                "pulse_rate": 72,
            })
        assert resp.status_code == 201

    async def test_pain_score_validation_422(self, client_provider: AsyncClient):
        with patch(
            "app.services.encounter_service.get_encounter_by_id",
            new_callable=AsyncMock,
            return_value=create_mock_encounter(id=ENC_ID),
        ):
            resp = await client_provider.post(f"{API}/{ENC_ID}/vitals", json={
                "pain_score": 11,  # max is 10
            })
        assert resp.status_code == 422

    async def test_oxygen_saturation_validation_422(self, client_provider: AsyncClient):
        with patch(
            "app.services.encounter_service.get_encounter_by_id",
            new_callable=AsyncMock,
            return_value=create_mock_encounter(id=ENC_ID),
        ):
            resp = await client_provider.post(f"{API}/{ENC_ID}/vitals", json={
                "oxygen_saturation": 101,  # max is 100
            })
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════
#  Cross-cutting: encounter not found on sub-resource ops
# ═══════════════════════════════════════════════════════════════

class TestEncounterNotFoundForSubResources:
    """When validate_encounter_exists fails, sub-resource endpoints should 404."""

    async def test_notes_parent_not_found(self, client_provider: AsyncClient):
        with patch(
            "app.services.encounter_service.get_encounter_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client_provider.post(f"{API}/{uuid.uuid4()}/notes", json={
                "note_type": "SOAP",
            })
        assert resp.status_code == 404

    async def test_orders_parent_not_found(self, client_provider: AsyncClient):
        with patch(
            "app.services.encounter_service.get_encounter_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client_provider.post(f"{API}/{uuid.uuid4()}/orders", json={
                "order_type": "LAB",
                "order_description": "CBC",
            })
        assert resp.status_code == 404

    async def test_vitals_parent_not_found(self, client_provider: AsyncClient):
        with patch(
            "app.services.encounter_service.get_encounter_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client_provider.post(f"{API}/{uuid.uuid4()}/vitals", json={
                "blood_pressure_systolic": 120,
            })
        assert resp.status_code == 404
