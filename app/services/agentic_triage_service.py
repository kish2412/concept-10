import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.patient_background import PatientBackground
from app.services.encounter_service import get_encounter_by_id


@dataclass
class TriageSummaryResult:
    encounter_id: uuid.UUID
    summary: str
    clinician_focus_points: list[str]
    red_flags: list[str]
    missing_information: list[str]
    generated_at: datetime
    orchestration: str
    model_provider: str
    model_name: str
    guardrail_profile: str | None


def _strip_html(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()


def _derive_chief_complaint(chief_complaint: str | None, note_fields: list[str]) -> str | None:
    if chief_complaint and chief_complaint.strip():
        return chief_complaint.strip()

    for field in note_fields:
        text = _strip_html(field)
        if not text:
            continue
        match = re.search(r"(?:chief\s*complaint|cc)\s*[:\-]\s*(.+)", text, flags=re.IGNORECASE)
        if match and match.group(1).strip():
            return match.group(1).strip()

    for field in note_fields:
        text = _strip_html(field)
        if text:
            return text
    return None


def _format_vitals_line(vitals) -> str | None:
    if not vitals:
        return None

    chunks: list[str] = []
    if vitals.blood_pressure_systolic is not None and vitals.blood_pressure_diastolic is not None:
        chunks.append(f"BP {vitals.blood_pressure_systolic}/{vitals.blood_pressure_diastolic} mmHg")
    if vitals.pulse_rate is not None:
        chunks.append(f"HR {vitals.pulse_rate} bpm")
    if vitals.respiratory_rate is not None:
        chunks.append(f"RR {vitals.respiratory_rate}/min")
    if vitals.temperature is not None:
        chunks.append(f"Temp {vitals.temperature} F")
    if vitals.oxygen_saturation is not None:
        chunks.append(f"SpO2 {vitals.oxygen_saturation}%")
    if vitals.pain_score is not None:
        chunks.append(f"Pain {vitals.pain_score}/10")

    return ", ".join(chunks) if chunks else None


def _collect_red_flags(vitals) -> list[str]:
    flags: list[str] = []
    if not vitals:
        return flags

    if vitals.oxygen_saturation is not None and float(vitals.oxygen_saturation) < 92:
        flags.append("Low oxygen saturation (<92%)")
    if vitals.temperature is not None and float(vitals.temperature) >= 101.3:
        flags.append("Fever (>=101.3 F)")
    if vitals.pulse_rate is not None and float(vitals.pulse_rate) >= 120:
        flags.append("Tachycardia (HR >=120 bpm)")
    if vitals.respiratory_rate is not None and float(vitals.respiratory_rate) >= 24:
        flags.append("Tachypnea (RR >=24/min)")
    if (
        vitals.blood_pressure_systolic is not None
        and vitals.blood_pressure_diastolic is not None
        and (int(vitals.blood_pressure_systolic) >= 180 or int(vitals.blood_pressure_diastolic) >= 120)
    ):
        flags.append("Hypertensive crisis range blood pressure")
    if vitals.pain_score is not None and int(vitals.pain_score) >= 8:
        flags.append("Severe pain score (>=8/10)")

    return flags


async def generate_triage_summary(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    encounter_id: uuid.UUID,
    guardrail_profile: str | None,
) -> TriageSummaryResult | None:
    encounter = await get_encounter_by_id(db=db, clinic_id=clinic_id, encounter_id=encounter_id)
    if not encounter:
        return None

    sorted_vitals = sorted(
        [v for v in encounter.vitals if not v.is_deleted],
        key=lambda v: (v.recorded_at or v.created_at),
        reverse=True,
    )
    latest_vitals = sorted_vitals[0] if sorted_vitals else None

    note_fields: list[str] = []
    for note in sorted(encounter.notes, key=lambda n: n.created_at, reverse=True):
        if note.is_deleted:
            continue
        note_fields.extend([note.subjective or "", note.objective or "", note.assessment or "", note.plan or ""])

    chief_complaint = _derive_chief_complaint(encounter.chief_complaint, note_fields)

    bg_result = await db.execute(
        select(PatientBackground).where(
            PatientBackground.clinic_id == clinic_id,
            PatientBackground.patient_id == encounter.patient_id,
            PatientBackground.is_deleted.is_(False),
        )
    )
    background = bg_result.scalar_one_or_none()

    chronic_conditions = [
        f"{dx.icd_code} {dx.icd_description}"
        for dx in encounter.diagnoses
        if not dx.is_deleted and dx.is_chronic_condition
    ]

    focus_points: list[str] = []
    if chief_complaint:
        focus_points.append(f"Primary concern to assess: {chief_complaint}")
    if chronic_conditions:
        focus_points.append(
            "Review chronic conditions that can affect current diagnosis: "
            + "; ".join(chronic_conditions[:3])
        )
    if latest_vitals and latest_vitals.pain_score is not None:
        focus_points.append(f"Correlate symptom severity with reported pain score ({latest_vitals.pain_score}/10)")

    red_flags = _collect_red_flags(latest_vitals)

    missing_information: list[str] = []
    if not chief_complaint:
        missing_information.append("Chief complaint is missing")
    if not latest_vitals:
        missing_information.append("No vitals recorded yet")
    if not background or not (background.medical_history and background.medical_history.strip()):
        missing_information.append("Prior medical history is incomplete")

    vitals_line = _format_vitals_line(latest_vitals)
    summary_parts = [
        f"Encounter {encounter.encounter_id} is currently in {encounter.status} stage.",
        f"Chief complaint: {chief_complaint}." if chief_complaint else "Chief complaint not documented.",
        f"Latest vitals: {vitals_line}." if vitals_line else "Latest vitals are not yet available.",
        (
            "Relevant prior medical history: "
            f"{background.medical_history.strip()[:400]}."
            if background and background.medical_history and background.medical_history.strip()
            else "Relevant prior medical history is not documented."
        ),
    ]

    if red_flags:
        summary_parts.append("Potential red flags: " + "; ".join(red_flags) + ".")

    if not focus_points:
        focus_points.append("Gather focused symptom timeline and complete exam before diagnosis.")

    return TriageSummaryResult(
        encounter_id=encounter_id,
        summary=" ".join(summary_parts),
        clinician_focus_points=focus_points,
        red_flags=red_flags,
        missing_information=missing_information,
        generated_at=datetime.now(timezone.utc),
        orchestration="triage_summary_v1",
        model_provider=settings.llm_provider,
        model_name=settings.llm_model,
        guardrail_profile=guardrail_profile,
    )
