import json
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.patient_background import PatientBackground
from app.services.encounter_service import get_encounter_by_id


logger = logging.getLogger(__name__)


TRIAGE_SUMMARY_SYSTEM_PROMPT = """
You are a senior clinical triage documentation assistant for licensed clinicians.
Generate a concise, structured triage summary using only provided encounter data.

Hard rules:
- Do not invent facts.
- If information is unavailable, state "Not documented".
- Separate observations from clinical focus suggestions.
- Do not provide definitive diagnosis.
- Explicitly call out urgent safety concerns.

Return strict JSON only with this shape:
{
    "summary": "string",
    "clinician_focus_points": ["string"],
    "red_flags": ["string"],
    "missing_information": ["string"]
}

Style:
- summary max 220 words.
- Clear, clinician-ready language.
- Include objective values when available.
""".strip()


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


def _merge_unique(primary: list[str], secondary: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for item in primary + secondary:
        normalized = (item or "").strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(normalized)
    return merged


def _extract_json_object(text: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    if not text:
        return None

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _normalize_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _calculate_age_years(date_of_birth: date | None) -> int:
    if not date_of_birth:
        return 0
    today = datetime.now(timezone.utc).date()
    years = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        years -= 1
    return max(years, 0)


def _gender_to_triage_sex(gender: str | None) -> str:
    value = (gender or "").strip().lower()
    if value in {"male", "m"}:
        return "M"
    if value in {"female", "f"}:
        return "F"
    if value:
        return "other"
    return "unknown"


def _nurse_concern_level(vitals, red_flags: list[str]) -> str:
    if red_flags:
        return "emergency"
    if not vitals:
        return "urgent"
    if vitals.pain_score is not None and int(vitals.pain_score) >= 7:
        return "urgent"
    return "routine"


def _pain_severity(pain_score: int | None) -> str:
    if pain_score is None:
        return "moderate"
    if pain_score >= 8:
        return "critical"
    if pain_score >= 5:
        return "severe"
    if pain_score >= 3:
        return "moderate"
    return "mild"


def _parse_current_medications(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    return [item.strip() for item in re.split(r"\r?\n|;", raw_value) if item.strip()]


def _specialist_triage_url() -> str | None:
    base = (settings.agentic_service_base_url or "").strip()
    if not base:
        return None
    trimmed = base.rstrip("/")
    if trimmed.endswith("/specialist"):
        return f"{trimmed}/triage/summarise"
    return f"{trimmed}/specialist/triage/summarise"


def _build_specialist_triage_payload(
    encounter,
    background: PatientBackground | None,
    latest_vitals,
    chief_complaint: str | None,
    red_flags: list[str],
    note_fields: list[str],
) -> dict[str, Any]:
    triage_assessment = encounter.triage_assessment if isinstance(encounter.triage_assessment, dict) else {}
    presenting_symptoms = triage_assessment.get("presenting_symptoms")
    if not isinstance(presenting_symptoms, list) or not presenting_symptoms:
        presenting_symptoms = [chief_complaint] if chief_complaint else ["Not documented"]

    pain_score = None
    if triage_assessment.get("pain_score") is not None:
        try:
            pain_score = int(triage_assessment["pain_score"])
        except (TypeError, ValueError):
            pain_score = None
    elif latest_vitals and latest_vitals.pain_score is not None:
        pain_score = int(latest_vitals.pain_score)

    recent_note_text = " ".join([_strip_html(item)[:220] for item in note_fields[:4] if _strip_html(item)]).strip()
    if not recent_note_text:
        recent_note_text = "Not documented"

    patient = encounter.patient
    known_allergies = patient.allergies if patient and isinstance(patient.allergies, list) else []

    return {
        "visit_id": encounter.encounter_id,
        "patient_id": str(encounter.patient_id),
        "request_id": str(uuid.uuid4()),
        "vitals": {
            "temperature_celsius": float(latest_vitals.temperature) if latest_vitals and latest_vitals.temperature is not None else None,
            "heart_rate_bpm": int(latest_vitals.pulse_rate) if latest_vitals and latest_vitals.pulse_rate is not None else None,
            "respiratory_rate_rpm": int(latest_vitals.respiratory_rate) if latest_vitals and latest_vitals.respiratory_rate is not None else None,
            "systolic_bp_mmhg": int(latest_vitals.blood_pressure_systolic) if latest_vitals and latest_vitals.blood_pressure_systolic is not None else None,
            "diastolic_bp_mmhg": int(latest_vitals.blood_pressure_diastolic) if latest_vitals and latest_vitals.blood_pressure_diastolic is not None else None,
            "spo2_percent": float(latest_vitals.oxygen_saturation) if latest_vitals and latest_vitals.oxygen_saturation is not None else None,
            "gcs_score": None,
            "pain_score": pain_score,
            "weight_kg": float(latest_vitals.weight) if latest_vitals and latest_vitals.weight is not None else None,
            "height_cm": float(latest_vitals.height) if latest_vitals and latest_vitals.height is not None else None,
        },
        "chief_complaint": {
            "primary_complaint": chief_complaint or "Not documented",
            "onset_description": triage_assessment.get("symptom_onset"),
            "duration_minutes": None,
            "severity": _pain_severity(pain_score),
            "associated_symptoms": [str(item).strip() for item in presenting_symptoms if str(item).strip()],
        },
        "patient_context": {
            "age_years": _calculate_age_years(patient.date_of_birth if patient else None),
            "sex": _gender_to_triage_sex(patient.gender if patient else None),
            "is_pregnant": False,
            "gestational_weeks": None,
            "known_allergies": known_allergies,
            "current_medications": _parse_current_medications(background.current_medications if background else None),
            "relevant_history": [
                item
                for item in [
                    background.medical_history.strip() if background and background.medical_history else "",
                    background.surgical_history.strip() if background and background.surgical_history else "",
                    background.family_history.strip() if background and background.family_history else "",
                ]
                if item
            ],
            "mobility_status": (triage_assessment.get("mobility_status") or "ambulatory") if isinstance(triage_assessment, dict) else "ambulatory",
            "communication_barrier": False,
            "preferred_language": "en",
            "arrived_by": "walk_in",
        },
        "nurse_notes": {
            "free_text": recent_note_text,
            "nurse_initial_concern": _nurse_concern_level(latest_vitals, red_flags),
            "nurse_id": str(encounter.updated_by or encounter.created_by or encounter.provider_id or "system"),
            "assessment_timestamp": (latest_vitals.recorded_at if latest_vitals and latest_vitals.recorded_at else datetime.now(timezone.utc)).isoformat(),
        },
        "triage_start_timestamp": (encounter.triage_at or datetime.now(timezone.utc)).isoformat(),
    }


async def _generate_specialist_triage_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], str | None] | None:
    url = _specialist_triage_url()
    if not settings.agentic_enabled or not url:
        return None

    token = (settings.agentic_service_token or "local-agentic-service-token").strip()
    headers = {
        "Authorization": f"Bearer {token}",
        "X-User-Role": settings.agentic_service_role,
    }

    try:
        timeout = max(int(settings.agentic_service_timeout_seconds), 1)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)

        if response.status_code >= 400:
            logger.warning(
                "Specialist triage request failed",
                extra={
                    "status_code": response.status_code,
                    "service_url": url,
                    "response_text": response.text[:500],
                },
            )
            return None

        content = response.json()
        if not isinstance(content, dict):
            return None

        return content, response.headers.get("X-LangSmith-URL")
    except Exception:
        logger.exception(
            "Specialist triage request exception",
            extra={"service_url": url},
        )
        return None


async def _generate_llm_triage_payload(context: dict[str, Any]) -> dict[str, Any] | None:
    if settings.llm_provider.lower() != "openai" or not settings.openai_api_key:
        logger.info(
            "Triage LLM skipped: provider/key not configured",
            extra={
                "llm_provider": settings.llm_provider,
                "has_openai_key": bool(settings.openai_api_key),
            },
        )
        return None

    try:
        from openai import AsyncOpenAI  # pyright: ignore[reportMissingImports]

        kwargs: dict[str, Any] = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url

        client = AsyncOpenAI(**kwargs)
        logger.info(
            "Triage LLM request started",
            extra={
                "llm_provider": settings.llm_provider,
                "llm_model": settings.llm_model,
                "encounter_id": context.get("encounter_id"),
            },
        )
        response = await client.responses.create(
            model=settings.llm_model,
            input=[
                {"role": "system", "content": TRIAGE_SUMMARY_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Generate triage summary JSON from this encounter context. "
                        "Use only facts in the payload.\\n"
                        f"{json.dumps(context, ensure_ascii=True)}"
                    ),
                },
            ],
            temperature=0.1,
            max_output_tokens=500,
        )

        payload = _extract_json_object((response.output_text or "").strip())
        if not payload:
            logger.warning(
                "Triage LLM response parsing failed",
                extra={
                    "llm_provider": settings.llm_provider,
                    "llm_model": settings.llm_model,
                    "encounter_id": context.get("encounter_id"),
                },
            )
            return None

        summary = (payload.get("summary") or "").strip()
        if not summary:
            logger.warning(
                "Triage LLM response missing summary field",
                extra={
                    "llm_provider": settings.llm_provider,
                    "llm_model": settings.llm_model,
                    "encounter_id": context.get("encounter_id"),
                },
            )
            return None

        logger.info(
            "Triage LLM request succeeded",
            extra={
                "llm_provider": settings.llm_provider,
                "llm_model": settings.llm_model,
                "encounter_id": context.get("encounter_id"),
            },
        )

        return {
            "summary": summary,
            "clinician_focus_points": _normalize_str_list(payload.get("clinician_focus_points")),
            "red_flags": _normalize_str_list(payload.get("red_flags")),
            "missing_information": _normalize_str_list(payload.get("missing_information")),
        }
    except Exception:
        logger.exception(
            "Triage LLM request failed",
            extra={
                "llm_provider": settings.llm_provider,
                "llm_model": settings.llm_model,
                "encounter_id": context.get("encounter_id"),
            },
        )
        return None


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

    deterministic_summary = " ".join(summary_parts)

    llm_context = {
        "encounter_id": str(encounter.encounter_id),
        "encounter_status": encounter.status,
        "chief_complaint": chief_complaint or "Not documented",
        "latest_vitals": vitals_line or "Not documented",
        "relevant_prior_medical_history": (
            background.medical_history.strip()[:1200]
            if background and background.medical_history and background.medical_history.strip()
            else "Not documented"
        ),
        "chronic_conditions": chronic_conditions[:8],
        "detected_red_flags": red_flags,
        "detected_missing_information": missing_information,
        "recent_note_context": [_strip_html(field)[:240] for field in note_fields if _strip_html(field)][:8],
    }

    specialist_payload = _build_specialist_triage_payload(
        encounter=encounter,
        background=background,
        latest_vitals=latest_vitals,
        chief_complaint=chief_complaint,
        red_flags=red_flags,
        note_fields=note_fields,
    )

    langsmith_trace_url: str | None = None
    specialist_result = await _generate_specialist_triage_payload(specialist_payload)
    if specialist_result:
        specialist_data, langsmith_trace_url = specialist_result
        clinical_summary = specialist_data.get("clinical_summary") if isinstance(specialist_data.get("clinical_summary"), dict) else {}

        summary = " ".join(
            [
                str(clinical_summary.get("one_liner") or "").strip(),
                str(clinical_summary.get("presenting_problem") or "").strip(),
                str(clinical_summary.get("vital_signs_interpretation") or "").strip(),
            ]
        ).strip() or deterministic_summary

        specialist_focus = _normalize_str_list(clinical_summary.get("recommended_workup"))
        specialist_focus = _merge_unique(
            specialist_focus,
            _normalize_str_list(clinical_summary.get("key_risk_factors")),
        )
        specialist_focus = _merge_unique(
            specialist_focus,
            _normalize_str_list(clinical_summary.get("differential_considerations")),
        )

        specialist_red_flags = []
        emergency_flags = specialist_data.get("emergency_flags")
        if isinstance(emergency_flags, list):
            for item in emergency_flags:
                if isinstance(item, dict):
                    description = str(item.get("description") or "").strip()
                    if description:
                        specialist_red_flags.append(description)

        focus_points = _merge_unique(specialist_focus, focus_points)
        red_flags = _merge_unique(red_flags, specialist_red_flags)
        missing_information = _merge_unique(
            missing_information,
            _normalize_str_list(specialist_data.get("missing_information")),
        )
        orchestration = "triage_summary_specialist_agent"
        model_provider = "concept10-agentic"
        model_name = "triage-summary-agent"
        logger.info(
            "Triage summary generated via specialist agent",
            extra={
                "encounter_id": str(encounter_id),
                "orchestration": orchestration,
                "service_url": settings.agentic_service_base_url,
            },
        )
    else:
        llm_payload = await _generate_llm_triage_payload(llm_context)
        if llm_payload:
            summary = llm_payload["summary"]
            focus_points = _merge_unique(llm_payload["clinician_focus_points"], focus_points)
            red_flags = _merge_unique(red_flags, llm_payload["red_flags"])
            missing_information = _merge_unique(missing_information, llm_payload["missing_information"])
            orchestration = "triage_summary_v2_llm"
            model_provider = settings.llm_provider
            model_name = settings.llm_model
            logger.info(
                "Triage summary generated via LLM",
                extra={
                    "encounter_id": str(encounter_id),
                    "orchestration": orchestration,
                    "llm_provider": settings.llm_provider,
                    "llm_model": settings.llm_model,
                },
            )
        else:
            summary = deterministic_summary
            orchestration = "triage_summary_v1"
            model_provider = settings.llm_provider
            model_name = settings.llm_model
            logger.info(
                "Triage summary fallback to deterministic generator",
                extra={
                    "encounter_id": str(encounter_id),
                    "orchestration": orchestration,
                    "llm_provider": settings.llm_provider,
                    "llm_model": settings.llm_model,
                },
            )

    generated_at = datetime.now(timezone.utc)

    # Persist latest triage AI output on the encounter for retrieval/history snapshots.
    encounter.ai_triage_summary = summary
    encounter.ai_triage_focus_points = focus_points
    encounter.ai_triage_red_flags = red_flags
    encounter.ai_triage_missing_information = missing_information
    encounter.ai_triage_generated_at = generated_at
    encounter.ai_triage_orchestration = orchestration
    encounter.ai_triage_model_provider = model_provider
    encounter.ai_triage_model_name = model_name
    encounter.ai_triage_guardrail_profile = guardrail_profile

    db.add(encounter)
    await db.commit()

    return TriageSummaryResult(
        encounter_id=encounter_id,
        summary=summary,
        clinician_focus_points=focus_points,
        red_flags=red_flags,
        missing_information=missing_information,
        generated_at=generated_at,
        orchestration=orchestration,
        model_provider=model_provider,
        model_name=model_name,
        guardrail_profile=guardrail_profile,
        langsmith_trace_url=langsmith_trace_url,
    )
