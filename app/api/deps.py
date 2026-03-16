"""FastAPI dependency helpers."""
import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.rbac import UserContext, get_user_context
from app.models.clinic import Clinic


# ── Raw state accessors (low-level, prefer UserContext below) ─────────

def get_clinic_id(request: Request) -> str:
    clinic_id = getattr(request.state, "clinic_id", None)
    if not clinic_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing tenant context")
    return clinic_id


def get_user_id(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing user context")
    return user_id

# ── Clinic helpers ────────────────────────────────────────────────────

def parse_clinic_uuid(clinic_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(clinic_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant context") from exc


async def get_current_clinic(
    ctx: UserContext = Depends(get_user_context),
    db: AsyncSession = Depends(get_db),
) -> Clinic:
    result = await db.execute(
        select(Clinic).where(
            Clinic.id == ctx.clinic_uuid,
            Clinic.is_deleted.is_(False),
            Clinic.is_active.is_(True),
        )
    )
    clinic = result.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    return clinic
# ── AI feature guard ──────────────────────────────────────────────────

async def require_ai_enabled(
    clinic: Clinic = Depends(get_current_clinic),
) -> Clinic:
    if not settings.agentic_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI workflows are disabled")
    if not clinic.ai_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="AI features not enabled for this clinic")
    return clinic
