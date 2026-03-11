from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

class VitalSigns(BaseModel):
    temperature_celsius: float | None = None
    heart_rate_bpm: int | None = None
    respiratory_rate_rpm: int | None = None
    systolic_bp_mmhg: int | None = None
    diastolic_bp_mmhg: int | None = None
    spo2_percent: float | None = None
    gcs_score: int | None = Field(None, ge=3, le=15, description="Glasgow Coma Scale 3-15")
    pain_score: int | None = Field(None, ge=0, le=10)
    weight_kg: float | None = None
    height_cm: float | None = None


class ChiefComplaint(BaseModel):
    primary_complaint: str = Field(..., max_length=500)
    onset_description: str | None = None
    duration_minutes: int | None = None
    severity: Literal["mild", "moderate", "severe", "critical"] | None = None
    associated_symptoms: list[str] = Field(default_factory=list)


class PatientContext(BaseModel):
    age_years: int = Field(..., ge=0, le=130)
    sex: Literal["M", "F", "other", "unknown"]
    is_pregnant: bool = False
    gestational_weeks: int | None = None
    known_allergies: list[str] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    relevant_history: list[str] = Field(default_factory=list)
    mobility_status: Literal["ambulatory", "assisted", "non_ambulatory"] = "ambulatory"
    communication_barrier: bool = False
    preferred_language: str = "en"
    arrived_by: Literal["walk_in", "ambulance", "referred", "other"] = "walk_in"


class NurseAssessmentNotes(BaseModel):
    free_text: str = Field(..., max_length=2000)
    nurse_initial_concern: Literal["routine", "urgent", "emergency"] = "routine"
    nurse_id: str
    assessment_timestamp: datetime


class TriageInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    visit_id: str = Field(..., description="Unique outpatient visit ID")
    patient_id: str
    request_id: str
    vitals: VitalSigns
    chief_complaint: ChiefComplaint
    patient_context: PatientContext
    nurse_notes: NurseAssessmentNotes
    triage_start_timestamp: datetime


class AcuityLevel(str, Enum):
    IMMEDIATE = "IMMEDIATE"
    EMERGENT = "EMERGENT"
    URGENT = "URGENT"
    LESS_URGENT = "LESS_URGENT"
    NON_URGENT = "NON_URGENT"


class EmergencyFlag(BaseModel):
    flag_code: str
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    recommended_action: str
    escalation_sla_seconds: int


class SpecialHandlingFlag(BaseModel):
    code: Literal[
        "FALL_RISK",
        "BARIATRIC",
        "ISOLATION_REQUIRED",
        "COGNITIVE_IMPAIRMENT",
        "INTERPRETER_REQUIRED",
        "PAEDIATRIC",
        "OBSTETRIC",
        "PSYCHIATRIC",
        "VIOLENCE_RISK",
    ]
    rationale: str
    required_resources: list[str] = Field(default_factory=list)


class ClinicalSummary(BaseModel):
    one_liner: str = Field(..., max_length=200)
    presenting_problem: str
    vital_signs_interpretation: str
    key_risk_factors: list[str]
    differential_considerations: list[str]
    recommended_workup: list[str]


class TriageSummaryOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    visit_id: str
    request_id: str
    acuity_level: AcuityLevel
    acuity_rationale: str
    clinical_summary: ClinicalSummary
    emergency_flags: list[EmergencyFlag]
    special_handling_flags: list[SpecialHandlingFlag]
    immediate_action_required: bool
    alert_charge_nurse: bool
    alert_attending_physician: bool
    suggested_waiting_area: Literal["resuscitation", "acute", "subacute", "fast_track"]
    summary_generated_at: datetime
    model_confidence: float = Field(..., ge=0.0, le=1.0)
    disclaimer: str = "AI-generated clinical aid. Must be reviewed by qualified clinician."
