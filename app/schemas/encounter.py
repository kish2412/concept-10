import uuid
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


# ═════════════════════════════════════════════════════════════════════
#  Enums (for validation only — stored as strings in the DB)
# ═════════════════════════════════════════════════════════════════════

class EncounterType(str, Enum):
    CONSULTATION = "CONSULTATION"
    FOLLOW_UP = "FOLLOW_UP"
    EMERGENCY = "EMERGENCY"
    PROCEDURE = "PROCEDURE"
    TELECONSULT = "TELECONSULT"


class EncounterStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    CHECKED_IN = "CHECKED_IN"
    TRIAGE = "TRIAGE"
    WITH_PROVIDER = "WITH_PROVIDER"
    PENDING_RESULTS = "PENDING_RESULTS"
    PENDING_REVIEW = "PENDING_REVIEW"
    DISCHARGED = "DISCHARGED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"


class NoteType(str, Enum):
    SOAP = "SOAP"
    PROGRESS = "PROGRESS"
    PROCEDURE = "PROCEDURE"
    DISCHARGE = "DISCHARGE"


class DiagnosisType(str, Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    DIFFERENTIAL = "DIFFERENTIAL"
    RULE_OUT = "RULE_OUT"


class OrderType(str, Enum):
    LAB = "LAB"
    IMAGING = "IMAGING"
    MEDICATION = "MEDICATION"
    PROCEDURE = "PROCEDURE"
    REFERRAL = "REFERRAL"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    IN_PROGRESS = "IN_PROGRESS"
    RESULTED = "RESULTED"
    CANCELLED = "CANCELLED"


class OrderPriority(str, Enum):
    ROUTINE = "ROUTINE"
    URGENT = "URGENT"
    STAT = "STAT"


class DispositionType(str, Enum):
    DISCHARGE = "DISCHARGE"
    ADMIT = "ADMIT"
    REFER_ER = "REFER_ER"
    REFER_SPECIALIST = "REFER_SPECIALIST"
    OBSERVATION = "OBSERVATION"


# ═════════════════════════════════════════════════════════════════════
#  1. Encounter
# ═════════════════════════════════════════════════════════════════════

class EncounterCreate(BaseModel):
    patient_id: uuid.UUID
    provider_id: uuid.UUID | None = None
    facility_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    encounter_type: EncounterType = EncounterType.CONSULTATION
    status: EncounterStatus = EncounterStatus.SCHEDULED
    chief_complaint: str | None = None
    scheduled_at: datetime | None = None
    checked_in_at: datetime | None = None
    triage_at: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None


class EncounterUpdate(BaseModel):
    provider_id: uuid.UUID | None = None
    facility_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    encounter_type: EncounterType | None = None
    status: EncounterStatus | None = None
    chief_complaint: str | None = None
    scheduled_at: datetime | None = None
    checked_in_at: datetime | None = None
    triage_at: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None


class EncounterPatientSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    first_name: str
    last_name: str


# ── Child responses (forward-declared, filled below) ──

class VitalsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    blood_pressure_systolic: int | None
    blood_pressure_diastolic: int | None
    pulse_rate: float | None
    respiratory_rate: float | None
    temperature: float | None
    oxygen_saturation: float | None
    weight: float | None
    height: float | None
    bmi: float | None
    pain_score: int | None
    recorded_by: uuid.UUID | None
    recorded_at: datetime | None
    created_at: datetime


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    note_type: str
    subjective: str | None
    objective: str | None
    assessment: str | None
    plan: str | None
    author_id: uuid.UUID | None
    author_role: str | None
    is_signed: bool
    signed_at: datetime | None
    version: int
    created_at: datetime


class DiagnosisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    icd_code: str
    icd_description: str
    diagnosis_type: str
    onset_date: date | None
    is_chronic_condition: bool
    added_by: uuid.UUID | None
    created_at: datetime


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    order_type: str
    order_code: str | None
    order_description: str
    status: str
    priority: str
    ordered_by: uuid.UUID | None
    ordered_at: datetime | None
    result_summary: str | None
    created_at: datetime


class MedicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    drug_code: str | None
    drug_name: str
    generic_name: str | None
    dosage: str
    dosage_unit: str
    frequency: str
    route: str
    duration_days: int | None
    quantity: int | None
    special_instructions: str | None
    is_controlled_substance: bool
    prescribed_by: uuid.UUID | None
    prescribed_at: datetime | None
    created_at: datetime


class DispositionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    disposition_type: str
    follow_up_required: bool
    follow_up_in_days: int | None
    discharge_instructions: str | None
    activity_restrictions: str | None
    diet_instructions: str | None
    patient_education_materials: list | dict | None
    discharged_by: uuid.UUID | None
    discharged_at: datetime | None
    created_at: datetime


class EncounterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clinic_id: uuid.UUID
    encounter_id: str
    patient_id: uuid.UUID
    provider_id: uuid.UUID | None
    facility_id: uuid.UUID | None
    department_id: uuid.UUID | None
    encounter_type: str
    status: str
    chief_complaint: str | None
    ai_triage_summary: str | None = None
    ai_triage_focus_points: list[str] | None = None
    ai_triage_red_flags: list[str] | None = None
    ai_triage_missing_information: list[str] | None = None
    ai_triage_generated_at: datetime | None = None
    ai_triage_orchestration: str | None = None
    ai_triage_model_provider: str | None = None
    ai_triage_model_name: str | None = None
    ai_triage_guardrail_profile: str | None = None
    scheduled_at: datetime | None
    checked_in_at: datetime | None
    triage_at: datetime | None
    started_at: datetime | None
    ended_at: datetime | None
    created_by: uuid.UUID | None
    updated_by: uuid.UUID | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    patient: EncounterPatientSummary | None = None
    vitals: list[VitalsResponse] = []
    notes: list[NoteResponse] = []
    diagnoses: list[DiagnosisResponse] = []
    orders: list[OrderResponse] = []
    medications: list[MedicationResponse] = []
    disposition: DispositionResponse | None = None


class EncounterListResponse(BaseModel):
    items: list[EncounterResponse]
    page: int
    size: int
    total: int


# ═════════════════════════════════════════════════════════════════════
#  2. EncounterVitals
# ═════════════════════════════════════════════════════════════════════

class VitalsCreate(BaseModel):
    blood_pressure_systolic: int | None = None
    blood_pressure_diastolic: int | None = None
    pulse_rate: float | None = None
    respiratory_rate: float | None = None
    temperature: float | None = None
    oxygen_saturation: float | None = Field(default=None, ge=0, le=100)
    weight: float | None = None
    height: float | None = None
    pain_score: int | None = Field(default=None, ge=0, le=10)
    recorded_by: uuid.UUID | None = None
    recorded_at: datetime | None = None


class VitalsUpdate(BaseModel):
    blood_pressure_systolic: int | None = None
    blood_pressure_diastolic: int | None = None
    pulse_rate: float | None = None
    respiratory_rate: float | None = None
    temperature: float | None = None
    oxygen_saturation: float | None = Field(default=None, ge=0, le=100)
    weight: float | None = None
    height: float | None = None
    pain_score: int | None = Field(default=None, ge=0, le=10)
    recorded_by: uuid.UUID | None = None
    recorded_at: datetime | None = None


# ═════════════════════════════════════════════════════════════════════
#  3. EncounterNote (SOAP)
# ═════════════════════════════════════════════════════════════════════

class NoteCreate(BaseModel):
    note_type: NoteType = NoteType.SOAP
    subjective: str | None = None
    objective: str | None = None
    assessment: str | None = None
    plan: str | None = None
    author_id: uuid.UUID | None = None
    author_role: str | None = None


class NoteUpdate(BaseModel):
    note_type: NoteType | None = None
    subjective: str | None = None
    objective: str | None = None
    assessment: str | None = None
    plan: str | None = None
    is_signed: bool | None = None
    signed_at: datetime | None = None


# ═════════════════════════════════════════════════════════════════════
#  4. EncounterDiagnosis
# ═════════════════════════════════════════════════════════════════════

class DiagnosisCreate(BaseModel):
    icd_code: str
    icd_description: str
    diagnosis_type: DiagnosisType = DiagnosisType.PRIMARY
    onset_date: date | None = None
    is_chronic_condition: bool = False
    added_by: uuid.UUID | None = None


class DiagnosisUpdate(BaseModel):
    icd_code: str | None = None
    icd_description: str | None = None
    diagnosis_type: DiagnosisType | None = None
    onset_date: date | None = None
    is_chronic_condition: bool | None = None


# ═════════════════════════════════════════════════════════════════════
#  5. EncounterOrder
# ═════════════════════════════════════════════════════════════════════

class OrderCreate(BaseModel):
    order_type: OrderType
    order_code: str | None = None
    order_description: str
    status: OrderStatus = OrderStatus.PENDING
    priority: OrderPriority = OrderPriority.ROUTINE
    ordered_by: uuid.UUID | None = None
    ordered_at: datetime | None = None


class OrderUpdate(BaseModel):
    order_type: OrderType | None = None
    order_code: str | None = None
    order_description: str | None = None
    status: OrderStatus | None = None
    priority: OrderPriority | None = None
    result_summary: str | None = None


# ═════════════════════════════════════════════════════════════════════
#  6. EncounterMedication (Prescription)
# ═════════════════════════════════════════════════════════════════════

class MedicationCreate(BaseModel):
    drug_code: str | None = None
    drug_name: str
    generic_name: str | None = None
    dosage: str
    dosage_unit: str
    frequency: str
    route: str
    duration_days: int | None = None
    quantity: int | None = None
    special_instructions: str | None = None
    is_controlled_substance: bool = False
    prescribed_by: uuid.UUID | None = None
    prescribed_at: datetime | None = None


class MedicationUpdate(BaseModel):
    drug_code: str | None = None
    drug_name: str | None = None
    generic_name: str | None = None
    dosage: str | None = None
    dosage_unit: str | None = None
    frequency: str | None = None
    route: str | None = None
    duration_days: int | None = None
    quantity: int | None = None
    special_instructions: str | None = None
    is_controlled_substance: bool | None = None


# ═════════════════════════════════════════════════════════════════════
#  7. EncounterDisposition
# ═════════════════════════════════════════════════════════════════════

class DispositionCreate(BaseModel):
    disposition_type: DispositionType
    follow_up_required: bool = False
    follow_up_in_days: int | None = None
    discharge_instructions: str | None = None
    activity_restrictions: str | None = None
    diet_instructions: str | None = None
    patient_education_materials: list | dict | None = None
    discharged_by: uuid.UUID | None = None
    discharged_at: datetime | None = None


class DispositionUpdate(BaseModel):
    disposition_type: DispositionType | None = None
    follow_up_required: bool | None = None
    follow_up_in_days: int | None = None
    discharge_instructions: str | None = None
    activity_restrictions: str | None = None
    diet_instructions: str | None = None
    patient_education_materials: list | dict | None = None


# ═════════════════════════════════════════════════════════════════════
#  8. Status-only update
# ═════════════════════════════════════════════════════════════════════

class StatusUpdate(BaseModel):
    status: EncounterStatus


# ═════════════════════════════════════════════════════════════════════
#  9. AI Triage Summary
# ═════════════════════════════════════════════════════════════════════

class TriageSummaryGenerateRequest(BaseModel):
    regenerate: bool = False


class TriageSummaryResponse(BaseModel):
    encounter_id: uuid.UUID
    summary: str
    clinician_focus_points: list[str]
    red_flags: list[str]
    missing_information: list[str]
    generated_at: datetime
    orchestration: str
    model_provider: str
    model_name: str
    guardrail_profile: str | None = None


# ═════════════════════════════════════════════════════════════════════
#  10. Agentic Clinical Assistants
# ═════════════════════════════════════════════════════════════════════

class AgentInvocationRequest(BaseModel):
    regenerate: bool = False


class DifferentialDiagnosisItem(BaseModel):
    diagnosis: str
    probability: float = Field(ge=0, le=1)
    rationale: str


class DifferentialDiagnosisResponse(BaseModel):
    encounter_id: uuid.UUID
    shortlist: list[DifferentialDiagnosisItem]
    suggested_next_steps: list[str]
    missing_information: list[str]
    generated_at: datetime
    orchestration: str
    model_provider: str
    model_name: str
    guardrail_profile: str | None = None


class OrderRecommendationItem(BaseModel):
    order_type: str
    order_description: str
    priority: str
    rationale: str


class OrderRecommendationResponse(BaseModel):
    encounter_id: uuid.UUID
    recommendations: list[OrderRecommendationItem]
    contraindications_or_cautions: list[str]
    generated_at: datetime
    orchestration: str
    model_provider: str
    model_name: str
    guardrail_profile: str | None = None


class MedicationSafetyAlert(BaseModel):
    severity: str
    message: str
    recommended_action: str


class MedicationSafetyResponse(BaseModel):
    encounter_id: uuid.UUID
    alerts: list[MedicationSafetyAlert]
    safe_to_prescribe: bool
    generated_at: datetime
    orchestration: str
    model_provider: str
    model_name: str
    guardrail_profile: str | None = None


class DispositionRiskResponse(BaseModel):
    encounter_id: uuid.UUID
    recommendation: str
    readmission_risk_score: float = Field(ge=0, le=1)
    risk_factors: list[str]
    follow_up_plan: list[str]
    generated_at: datetime
    orchestration: str
    model_provider: str
    model_name: str
    guardrail_profile: str | None = None


class DocumentationQualityIssue(BaseModel):
    section: str
    issue: str
    suggested_fix: str


class DocumentationQualityResponse(BaseModel):
    encounter_id: uuid.UUID
    score: int = Field(ge=0, le=100)
    issues: list[DocumentationQualityIssue]
    generated_at: datetime
    orchestration: str
    model_provider: str
    model_name: str
    guardrail_profile: str | None = None


class PriorEncounterSummaryResponse(BaseModel):
    encounter_id: uuid.UUID
    prior_encounter_count: int
    timeline_summary: str
    recurring_patterns: list[str]
    generated_at: datetime
    orchestration: str
    model_provider: str
    model_name: str
    guardrail_profile: str | None = None


# ═════════════════════════════════════════════════════════════════════
#  9. Today summary response
# ═════════════════════════════════════════════════════════════════════

class TodaySummary(BaseModel):
    total: int
    by_status: dict[str, int]
    by_type: dict[str, int]
    discharged_by: uuid.UUID | None = None
    discharged_at: datetime | None = None
