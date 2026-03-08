import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.encounter import Encounter
from app.models.patient_background import PatientBackground
from app.services.encounter_service import get_encounter_by_id


@dataclass
class AgentMeta:
    generated_at: datetime
    model_provider: str
    model_name: str


def _strip_html(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()


def _derive_chief_complaint(encounter) -> str | None:
    direct = (encounter.chief_complaint or "").strip()
    if direct:
        return direct

    for note in sorted(encounter.notes, key=lambda n: n.created_at, reverse=True):
        if note.is_deleted:
            continue
        for field in [note.subjective, note.objective, note.assessment, note.plan]:
            text = _strip_html(field)
            if not text:
                continue
            match = re.search(r"(?:chief\s*complaint|cc)\s*[:\-]\s*(.+)", text, flags=re.IGNORECASE)
            if match and match.group(1).strip():
                return match.group(1).strip()
            return text
    return None


def _latest_vitals(encounter):
    vitals = [v for v in encounter.vitals if not v.is_deleted]
    vitals.sort(key=lambda v: (v.recorded_at or v.created_at), reverse=True)
    return vitals[0] if vitals else None


def _agent_meta() -> AgentMeta:
    return AgentMeta(
        generated_at=datetime.now(timezone.utc),
        model_provider=settings.llm_provider,
        model_name=settings.llm_model,
    )


async def _model_hint(prompt: str) -> str | None:
    if settings.llm_provider.lower() != "openai" or not settings.openai_api_key:
        return None

    try:
        from openai import AsyncOpenAI  # pyright: ignore[reportMissingImports]

        kwargs = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url

        client = AsyncOpenAI(**kwargs)
        completion = await client.responses.create(
            model=settings.llm_model,
            input=[
                {
                    "role": "system",
                    "content": "You are a clinical co-pilot. Provide concise, safety-first assistance.",
                },
                {"role": "user", "content": prompt[:5000]},
            ],
            max_output_tokens=200,
            temperature=0.1,
        )
        return (completion.output_text or "").strip() or None
    except Exception:
        return None


async def _load_context(db: AsyncSession, clinic_id: uuid.UUID, encounter_id: uuid.UUID):
    encounter = await get_encounter_by_id(db=db, clinic_id=clinic_id, encounter_id=encounter_id)
    if not encounter:
        return None

    background_result = await db.execute(
        select(PatientBackground).where(
            PatientBackground.clinic_id == clinic_id,
            PatientBackground.patient_id == encounter.patient_id,
            PatientBackground.is_deleted.is_(False),
        )
    )
    background = background_result.scalar_one_or_none()

    prior_result = await db.execute(
        select(Encounter)
        .where(
            Encounter.clinic_id == clinic_id,
            Encounter.patient_id == encounter.patient_id,
            Encounter.id != encounter_id,
            Encounter.is_deleted.is_(False),
            Encounter.deleted_at.is_(None),
        )
        .order_by(Encounter.created_at.desc())
        .limit(5)
    )
    prior_encounters = list(prior_result.scalars().all())

    return encounter, background, prior_encounters


async def run_differential_diagnosis_agent(db: AsyncSession, clinic_id: uuid.UUID, encounter_id: uuid.UUID):
    loaded = await _load_context(db, clinic_id, encounter_id)
    if not loaded:
        return None
    encounter, background, _ = loaded
    chief = _derive_chief_complaint(encounter)
    vitals = _latest_vitals(encounter)

    shortlist = [
        {
            "diagnosis": "Undifferentiated acute condition",
            "probability": 0.45,
            "rationale": "Initial triage context is limited; start broad and narrow with focused exam.",
        },
        {
            "diagnosis": "Infectious etiology",
            "probability": 0.3,
            "rationale": "Consider if fever, inflammatory symptoms, or recent exposure are present.",
        },
        {
            "diagnosis": "Chronic disease exacerbation",
            "probability": 0.25,
            "rationale": "Past history and known chronic diagnoses may explain current presentation.",
        },
    ]

    if chief and "chest" in chief.lower():
        shortlist = [
            {
                "diagnosis": "Acute coronary syndrome",
                "probability": 0.4,
                "rationale": "Chest pain warrants immediate cardiac risk stratification.",
            },
            {
                "diagnosis": "Musculoskeletal chest pain",
                "probability": 0.35,
                "rationale": "Common benign etiology if pain is reproducible and vitals are stable.",
            },
            {
                "diagnosis": "Pulmonary cause (PE/pneumonia)",
                "probability": 0.25,
                "rationale": "Consider with dyspnea, hypoxia, fever, or pleuritic symptoms.",
            },
        ]

    missing = []
    if not chief:
        missing.append("Chief complaint is missing")
    if not vitals:
        missing.append("No recent vitals")
    if not background or not (background.medical_history or "").strip():
        missing.append("Past medical history is incomplete")

    next_steps = [
        "Perform focused history and exam to discriminate top differential diagnoses",
        "Order baseline diagnostics guided by red flags and chief complaint",
        "Reassess differential after initial test results",
    ]

    model_text = await _model_hint(
        f"Chief complaint: {chief or 'N/A'}. Provide 1 additional high-yield next step for differential diagnosis."
    )
    if model_text:
        next_steps.append(model_text)

    meta = _agent_meta()
    return {
        "encounter_id": encounter_id,
        "shortlist": shortlist,
        "suggested_next_steps": next_steps,
        "missing_information": missing,
        "generated_at": meta.generated_at,
        "orchestration": "differential_diagnosis_v1",
        "model_provider": meta.model_provider,
        "model_name": meta.model_name,
    }


async def run_order_recommendation_agent(db: AsyncSession, clinic_id: uuid.UUID, encounter_id: uuid.UUID):
    loaded = await _load_context(db, clinic_id, encounter_id)
    if not loaded:
        return None
    encounter, _, _ = loaded
    chief = _derive_chief_complaint(encounter) or "undifferentiated complaint"

    recommendations = [
        {
            "order_type": "LAB",
            "order_description": "CBC, CMP, CRP",
            "priority": "ROUTINE",
            "rationale": f"Baseline workup for {chief}.",
        },
        {
            "order_type": "LAB",
            "order_description": "Urinalysis",
            "priority": "ROUTINE",
            "rationale": "Useful for broad triage in undifferentiated cases.",
        },
    ]

    cautions = []
    if chief and "chest" in chief.lower():
        recommendations = [
            {
                "order_type": "LAB",
                "order_description": "Troponin, CBC, CMP",
                "priority": "STAT",
                "rationale": "Rule out acute coronary syndrome and establish baseline labs.",
            },
            {
                "order_type": "IMAGING",
                "order_description": "Chest X-ray",
                "priority": "URGENT",
                "rationale": "Screen for pulmonary or mediastinal pathology.",
            },
            {
                "order_type": "PROCEDURE",
                "order_description": "12-lead ECG",
                "priority": "STAT",
                "rationale": "Immediate rhythm and ischemia assessment.",
            },
        ]
        cautions.append("Escalate immediately if dynamic ECG changes or hemodynamic instability occur")

    meta = _agent_meta()
    return {
        "encounter_id": encounter_id,
        "recommendations": recommendations,
        "contraindications_or_cautions": cautions,
        "generated_at": meta.generated_at,
        "orchestration": "orders_recommendation_v1",
        "model_provider": meta.model_provider,
        "model_name": meta.model_name,
    }


async def run_medication_safety_agent(db: AsyncSession, clinic_id: uuid.UUID, encounter_id: uuid.UUID):
    loaded = await _load_context(db, clinic_id, encounter_id)
    if not loaded:
        return None
    encounter, _, _ = loaded

    alerts = []
    allergies = encounter.patient.allergies if encounter.patient else []
    for med in encounter.medications:
        if med.is_deleted:
            continue
        for allergy in allergies:
            if allergy.lower() in med.drug_name.lower():
                alerts.append(
                    {
                        "severity": "high",
                        "message": f"Potential allergy conflict: {med.drug_name} vs allergy '{allergy}'.",
                        "recommended_action": "Hold medication and verify allergy details before prescribing.",
                    }
                )

        if med.is_controlled_substance:
            alerts.append(
                {
                    "severity": "medium",
                    "message": f"Controlled substance prescribed: {med.drug_name}.",
                    "recommended_action": "Confirm indication, duration, and regulatory documentation.",
                }
            )

    meta = _agent_meta()
    return {
        "encounter_id": encounter_id,
        "alerts": alerts,
        "safe_to_prescribe": len([a for a in alerts if a["severity"] == "high"]) == 0,
        "generated_at": meta.generated_at,
        "orchestration": "medication_safety_v1",
        "model_provider": meta.model_provider,
        "model_name": meta.model_name,
    }


async def run_disposition_risk_agent(db: AsyncSession, clinic_id: uuid.UUID, encounter_id: uuid.UUID):
    loaded = await _load_context(db, clinic_id, encounter_id)
    if not loaded:
        return None
    encounter, _, prior_encounters = loaded

    score = 0.2
    factors = []

    chronic_dx_count = len([d for d in encounter.diagnoses if not d.is_deleted and d.is_chronic_condition])
    if chronic_dx_count >= 2:
        score += 0.2
        factors.append("Multiple chronic conditions")

    if len(prior_encounters) >= 3:
        score += 0.15
        factors.append("Frequent recent encounters")

    vitals = _latest_vitals(encounter)
    if vitals and vitals.oxygen_saturation is not None and float(vitals.oxygen_saturation) < 92:
        score += 0.25
        factors.append("Low oxygen saturation")

    if vitals and vitals.pain_score is not None and int(vitals.pain_score) >= 8:
        score += 0.1
        factors.append("High pain burden")

    score = min(score, 1.0)
    recommendation = "DISCHARGE with close follow-up" if score < 0.45 else "CONSIDER ADMISSION / OBSERVATION"

    follow_up = [
        "Schedule follow-up within 48-72 hours for moderate/high risk",
        "Provide return precautions in plain language",
        "Confirm medication reconciliation and adherence plan",
    ]

    meta = _agent_meta()
    return {
        "encounter_id": encounter_id,
        "recommendation": recommendation,
        "readmission_risk_score": round(score, 2),
        "risk_factors": factors,
        "follow_up_plan": follow_up,
        "generated_at": meta.generated_at,
        "orchestration": "disposition_risk_v1",
        "model_provider": meta.model_provider,
        "model_name": meta.model_name,
    }


async def run_documentation_quality_agent(db: AsyncSession, clinic_id: uuid.UUID, encounter_id: uuid.UUID):
    loaded = await _load_context(db, clinic_id, encounter_id)
    if not loaded:
        return None
    encounter, background, _ = loaded

    issues = []
    score = 100

    chief = _derive_chief_complaint(encounter)
    if not chief:
        issues.append(
            {
                "section": "Chief Complaint",
                "issue": "Chief complaint is missing or unclear.",
                "suggested_fix": "Add concise symptom statement and onset context.",
            }
        )
        score -= 20

    signed_notes = [n for n in encounter.notes if not n.is_deleted and n.is_signed]
    if not signed_notes:
        issues.append(
            {
                "section": "Clinical Notes",
                "issue": "No signed note found.",
                "suggested_fix": "Sign SOAP/progress note before disposition.",
            }
        )
        score -= 25

    if not encounter.diagnoses:
        issues.append(
            {
                "section": "Diagnosis",
                "issue": "No diagnosis documented.",
                "suggested_fix": "Add at least one working or confirmed diagnosis.",
            }
        )
        score -= 20

    if not background or not (background.medical_history or "").strip():
        issues.append(
            {
                "section": "History",
                "issue": "Past medical history is incomplete.",
                "suggested_fix": "Document key chronic illnesses, surgeries, and relevant social history.",
            }
        )
        score -= 15

    if encounter.status == "DISCHARGED" and not encounter.disposition:
        issues.append(
            {
                "section": "Disposition",
                "issue": "Encounter discharged without disposition details.",
                "suggested_fix": "Capture disposition type and discharge/follow-up instructions.",
            }
        )
        score -= 20

    meta = _agent_meta()
    return {
        "encounter_id": encounter_id,
        "score": max(score, 0),
        "issues": issues,
        "generated_at": meta.generated_at,
        "orchestration": "documentation_quality_v1",
        "model_provider": meta.model_provider,
        "model_name": meta.model_name,
    }


async def run_prior_encounter_summary_agent(db: AsyncSession, clinic_id: uuid.UUID, encounter_id: uuid.UUID):
    loaded = await _load_context(db, clinic_id, encounter_id)
    if not loaded:
        return None
    _, _, prior_encounters = loaded

    if not prior_encounters:
        timeline_summary = "No prior encounters found for this patient in the current clinic."
        patterns: list[str] = []
    else:
        timeline_bits = []
        complaint_terms: dict[str, int] = {}
        for enc in prior_encounters:
            label = enc.encounter_id
            date_text = enc.created_at.strftime("%Y-%m-%d")
            complaint = (enc.chief_complaint or "No complaint documented").strip()
            timeline_bits.append(f"{date_text}: {label} - {complaint}")
            token = complaint.lower().split(" ")[0] if complaint else "unspecified"
            complaint_terms[token] = complaint_terms.get(token, 0) + 1

        timeline_summary = " | ".join(timeline_bits)
        patterns = [
            f"Recurring symptom theme: '{term}' ({count} encounters)"
            for term, count in sorted(complaint_terms.items(), key=lambda item: item[1], reverse=True)
            if count > 1
        ]

    meta = _agent_meta()
    return {
        "encounter_id": encounter_id,
        "prior_encounter_count": len(prior_encounters),
        "timeline_summary": timeline_summary,
        "recurring_patterns": patterns,
        "generated_at": meta.generated_at,
        "orchestration": "prior_encounter_summary_v1",
        "model_provider": meta.model_provider,
        "model_name": meta.model_name,
    }
