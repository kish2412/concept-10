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

    # All agentic/AI handling services removed from backend.
