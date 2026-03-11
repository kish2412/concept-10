from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from core.schemas.domains.triage import TriageInput, TriageSummaryOutput


def _valid_input_payload() -> dict:
    now = datetime.now(UTC)
    return {
        "visit_id": "visit-001",
        "patient_id": "patient-001",
        "request_id": "req-001",
        "vitals": {
            "temperature_celsius": 37.2,
            "heart_rate_bpm": 98,
            "respiratory_rate_rpm": 20,
            "systolic_bp_mmhg": 122,
            "diastolic_bp_mmhg": 80,
            "spo2_percent": 98.0,
            "gcs_score": 15,
            "pain_score": 5,
            "weight_kg": 72.4,
            "height_cm": 174.0,
        },
        "chief_complaint": {
            "primary_complaint": "Fever and cough",
            "onset_description": "Started yesterday",
            "duration_minutes": 1440,
            "severity": "moderate",
            "associated_symptoms": ["fatigue", "sore throat"],
        },
        "patient_context": {
            "age_years": 34,
            "sex": "F",
            "is_pregnant": False,
            "known_allergies": ["penicillin"],
            "current_medications": ["acetaminophen"],
            "relevant_history": ["asthma"],
            "mobility_status": "ambulatory",
            "communication_barrier": False,
            "preferred_language": "en",
            "arrived_by": "walk_in",
        },
        "nurse_notes": {
            "free_text": "Patient speaking in full sentences and appears mildly distressed.",
            "nurse_initial_concern": "routine",
            "nurse_id": "nurse-123",
            "assessment_timestamp": now,
        },
        "triage_start_timestamp": now,
    }


def _valid_output_payload() -> dict:
    now = datetime.now(UTC)
    return {
        "visit_id": "visit-001",
        "request_id": "req-001",
        "acuity_level": "URGENT",
        "acuity_rationale": "Stable but symptomatic with comorbidity risk.",
        "clinical_summary": {
            "one_liner": "34F with fever/cough, stable vitals, moderate pain.",
            "presenting_problem": "Upper respiratory symptoms with moderate discomfort.",
            "vital_signs_interpretation": "Vitals currently stable, no immediate compromise.",
            "key_risk_factors": ["asthma"],
            "differential_considerations": ["viral URI", "influenza"],
            "recommended_workup": ["CBC", "viral panel", "chest exam"],
        },
        "emergency_flags": [],
        "special_handling_flags": [
            {
                "code": "INTERPRETER_REQUIRED",
                "rationale": "Patient requested language support.",
                "required_resources": ["medical interpreter"],
            }
        ],
        "immediate_action_required": False,
        "alert_charge_nurse": False,
        "alert_attending_physician": False,
        "suggested_waiting_area": "subacute",
        "summary_generated_at": now,
        "model_confidence": 0.86,
    }


def test_triage_schema_valid_input_output_round_trip() -> None:
    input_model = TriageInput.model_validate(_valid_input_payload())
    output_model = TriageSummaryOutput.model_validate(_valid_output_payload())

    input_roundtrip = TriageInput.model_validate(input_model.model_dump())
    output_roundtrip = TriageSummaryOutput.model_validate(output_model.model_dump())

    assert input_roundtrip.visit_id == "visit-001"
    assert output_roundtrip.acuity_level.value == "URGENT"
    assert output_roundtrip.disclaimer.startswith("AI-generated clinical aid")


def test_triage_schema_rejects_extra_fields() -> None:
    bad_input = _valid_input_payload()
    bad_input["unexpected"] = "not-allowed"

    bad_output = _valid_output_payload()
    bad_output["extra"] = True

    with pytest.raises(ValidationError):
        TriageInput.model_validate(bad_input)

    with pytest.raises(ValidationError):
        TriageSummaryOutput.model_validate(bad_output)


def test_triage_schema_edge_cases() -> None:
    edge_input = _valid_input_payload()
    edge_input["vitals"]["gcs_score"] = 3
    edge_input["vitals"]["pain_score"] = 10
    edge_input["patient_context"]["is_pregnant"] = True
    edge_input["patient_context"].pop("gestational_weeks", None)

    model = TriageInput.model_validate(edge_input)

    assert model.vitals.gcs_score == 3
    assert model.vitals.pain_score == 10
    assert model.patient_context.is_pregnant is True
    assert model.patient_context.gestational_weeks is None
