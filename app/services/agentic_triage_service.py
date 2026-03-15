from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
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
    langsmith_trace_url: str | None


def _strip_html(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()


def _latest_vitals(encounter):
    vitals = [v for v in encounter.vitals if not getattr(v, "is_deleted", False)]
    vitals.sort(key=lambda v: (v.recorded_at or v.created_at), reverse=True)
    return vitals[0] if vitals else None


def _age_from_dob(dob) -> int | None:
    if not dob:
        return None
    today = datetime.now(timezone.utc).date()
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return max(years, 0)


def _best_note_text(encounter) -> str | None:
    if not encounter.notes:
        return None
    notes = sorted(encounter.notes, key=lambda n: n.created_at, reverse=True)
    for note in notes:
        if getattr(note, "is_deleted", False):
            continue
        for field in (note.subjective, note.objective, note.assessment, note.plan):
            text = _strip_html(field)
            if text:
                return text
    return None


def _deterministic_summary(encounter) -> tuple[str, list[str], list[str], list[str]]:
    triage = encounter.triage_assessment or {}
    presenting = triage.get("presenting_symptoms") or []
    red_flags = triage.get("red_flags") or []
    triage_notes = _strip_html(triage.get("triage_notes")) if triage else ""

    chief = _chief_complaint_text(encounter)

    focus_points: list[str] = []
    if presenting:
        focus_points.append(f"Presenting symptoms: {', '.join(presenting[:5])}")
    if triage_notes:
        focus_points.append("Review triage notes and symptom progression")
    if encounter.vitals:
        focus_points.append("Review latest vitals and trends")

    missing: list[str] = []
    if not encounter.vitals:
        missing.append("Recent vital signs")
    if not encounter.triage_assessment:
        missing.append("Formal triage assessment")
    if not triage_notes:
        missing.append("Triage notes / nursing narrative")
    if not encounter.chief_complaint and not presenting:
        missing.append("Chief complaint or presenting symptoms")

    summary = f"Patient presents with {chief}."
    if red_flags:
        summary += f" Reported red flags: {', '.join(red_flags[:5])}."

    return summary, focus_points, red_flags, missing


async def _load_background(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID):
    result = await db.execute(
        select(PatientBackground).where(
            PatientBackground.clinic_id == clinic_id,
            PatientBackground.patient_id == patient_id,
        )
    )
    return result.scalar_one_or_none()


def _build_agentic_payload(encounter, background) -> dict:
    vitals = _latest_vitals(encounter)
    patient = encounter.patient
    triage = encounter.triage_assessment or {}
    triage_notes = _strip_html(triage.get("triage_notes")) if triage else ""
    free_text = triage_notes or _best_note_text(encounter) or "No triage notes provided."
    assessment_ts = encounter.triage_at or encounter.created_at or datetime.now(timezone.utc)
    assessment_ts_iso = assessment_ts.isoformat()

    allergies = getattr(patient, "allergies", None) or []
    current_meds = _split_list(getattr(background, "current_medications", None))
    relevant_history = []
    relevant_history.extend(_split_list(getattr(background, "medical_history", None)))
    relevant_history.extend(_split_list(getattr(background, "surgical_history", None)))
    relevant_history.extend(_split_list(getattr(background, "family_history", None)))
    relevant_history.extend(_split_list(getattr(background, "social_history", None)))

    payload = {
        "visit_id": encounter.encounter_id,
        "patient_id": str(encounter.patient_id),
        "request_id": uuid.uuid4().hex,
        "vitals": {
            "temperature_celsius": float(vitals.temperature) if vitals and vitals.temperature is not None else None,
            "heart_rate_bpm": int(vitals.pulse_rate) if vitals and vitals.pulse_rate is not None else None,
            "respiratory_rate_rpm": int(vitals.respiratory_rate)
            if vitals and vitals.respiratory_rate is not None
            else None,
            "systolic_bp_mmhg": vitals.blood_pressure_systolic if vitals else None,
            "diastolic_bp_mmhg": vitals.blood_pressure_diastolic if vitals else None,
            "spo2_percent": float(vitals.oxygen_saturation)
            if vitals and vitals.oxygen_saturation is not None
            else None,
            "gcs_score": None,
            "pain_score": vitals.pain_score if vitals else None,
            "weight_kg": float(vitals.weight) if vitals and vitals.weight is not None else None,
            "height_cm": float(vitals.height) if vitals and vitals.height is not None else None,
        },
        "chief_complaint": {
            "primary_complaint": _chief_complaint_text(encounter),
            "onset_description": triage.get("symptom_onset"),
            "duration_minutes": None,
            "severity": None,
            "associated_symptoms": triage.get("presenting_symptoms") or [],
        },
        "patient_context": {
            "age_years": _age_from_dob(getattr(patient, "date_of_birth", None)) or 0,
            "sex": _normalize_sex(getattr(patient, "gender", None)),
            "is_pregnant": False,
            "gestational_weeks": None,
            "known_allergies": allergies,
            "current_medications": current_meds,
            "relevant_history": relevant_history,
            "mobility_status": "ambulatory",
            "communication_barrier": False,
            "preferred_language": "en",
            "arrived_by": "walk_in",
        },
        "nurse_notes": {
            "free_text": free_text,
            "nurse_initial_concern": "routine",
            "nurse_id": "system",
            "assessment_timestamp": assessment_ts_iso,
        },
        "triage_start_timestamp": assessment_ts_iso,
    }
    return payload


def _map_agentic_response(data: dict) -> tuple[str, list[str], list[str], list[str]]:
    clinical = data.get("clinical_summary") or {}
    summary = (
        clinical.get("one_liner")
        or clinical.get("presenting_problem")
        or "AI triage summary generated."
    )

    focus_points: list[str] = []
    for key in ("key_risk_factors", "differential_considerations", "recommended_workup"):
        values = clinical.get(key) or []
        if values:
            focus_points.append(f"{key.replace('_', ' ').title()}: {', '.join(values[:5])}")

    emergency_flags = data.get("emergency_flags") or []
    red_flags = [
        flag.get("description") or flag.get("flag_code")
        for flag in emergency_flags
        if isinstance(flag, dict)
    ]

    missing = data.get("missing_information") or []
    return summary, focus_points, red_flags, missing


async def generate_triage_summary(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    encounter_id: uuid.UUID,
    guardrail_profile: str | None = None,
) -> TriageSummaryResult | None:
    encounter = await get_encounter_by_id(db=db, clinic_id=clinic_id, encounter_id=encounter_id)
    if not encounter:
        return None

    generated_at = datetime.now(timezone.utc)

    if settings.agentic_enabled and settings.agentic_service_base_url and settings.agentic_service_token:
        payload = _build_agentic_payload(
            encounter=encounter,
            background=await _load_background(db, clinic_id, encounter.patient_id),
        )
        headers = {
            "Authorization": f"Bearer {settings.agentic_service_token}",
            "X-User-Role": settings.agentic_service_role,
        }
        url = f"{settings.agentic_service_base_url.rstrip('/')}/specialist/triage/summarise"
        try:
            timeout = httpx.Timeout(settings.agentic_service_timeout_seconds)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            summary, focus_points, red_flags, missing = _map_agentic_response(data)
            return TriageSummaryResult(
                encounter_id=encounter_id,
                summary=summary,
                clinician_focus_points=focus_points,
                red_flags=red_flags,
                missing_information=missing,
                generated_at=generated_at,
                orchestration="agentic",
                model_provider=settings.llm_provider,
                model_name=settings.llm_model,
                guardrail_profile=guardrail_profile,
                langsmith_trace_url=response.headers.get("X-LangSmith-URL")
                or response.headers.get("x-langsmith-url"),
            )
        except Exception:
            pass

    summary, focus_points, red_flags, missing = _deterministic_summary(encounter)
    return TriageSummaryResult(
        encounter_id=encounter_id,
        summary=summary,
        clinician_focus_points=focus_points,
        red_flags=red_flags,
        missing_information=missing,
        generated_at=generated_at,
        orchestration="deterministic",
        model_provider=settings.llm_provider,
        model_name=settings.llm_model,
        guardrail_profile=guardrail_profile,
        langsmith_trace_url=None,
    )
def _split_list(value: str | None) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[,\n;]+", value)
    return [item.strip() for item in parts if item.strip()]


def _normalize_sex(value: str | None) -> str:
    if not value:
        return "unknown"
    lowered = value.strip().lower()
    if lowered in {"m", "male"}:
        return "M"
    if lowered in {"f", "female"}:
        return "F"
    if lowered in {"other", "nonbinary", "non-binary"}:
        return "other"
    return "unknown"


def _chief_complaint_text(encounter) -> str:
    chief = (encounter.chief_complaint or "").strip()
    if chief:
        return chief
    triage = encounter.triage_assessment or {}
    presenting = triage.get("presenting_symptoms") or []
    if presenting:
        return ", ".join(presenting[:3])
    note = _best_note_text(encounter)
    if note:
        return note[:200]
    return "Unspecified complaint"
