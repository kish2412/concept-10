"""
app/api/v1/routes/webhooks.py
──────────────────────────────
Clerk webhook receiver. Syncs user lifecycle events to your DB.

Clerk dashboard setup:
  1. Webhooks → Add endpoint
  2. URL: https://your-api.railway.app/api/v1/webhooks/clerk
  3. Subscribe to: user.created, user.updated, user.deleted
  4. Copy Signing Secret → CLERK_WEBHOOK_SECRET in .env
"""
import hashlib
import hmac
import base64
import logging
import time
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.onboarding import PENDING_CLINIC_ID, ensure_pending_clinic
from app.models.user import User, UserRole

logger = logging.getLogger("app.webhooks")
router = APIRouter()


def _verify_svix(payload: bytes, svix_id: str, svix_ts: str, svix_sig: str, secret: str) -> bool:
    """Verify Svix webhook signature. https://docs.svix.com/receiving/verifying-payloads/how"""
    try:
        key = base64.b64decode(secret.removeprefix("whsec_"))
        signed = f"{svix_id}.{svix_ts}.{payload.decode()}".encode()
        mac = hmac.new(key, signed, hashlib.sha256)
        expected = base64.b64encode(mac.digest()).decode()
        return any(
            hmac.compare_digest(sig.removeprefix("v1,"), expected)
            for sig in svix_sig.split(" ")
            if sig.startswith("v1,")
        )
    except Exception:
        return False


@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    svix_id: str = Header(..., alias="svix-id"),
    svix_timestamp: str = Header(..., alias="svix-timestamp"),
    svix_signature: str = Header(..., alias="svix-signature"),
):
    payload = await request.body()

    if not settings.clerk_webhook_secret:
        logger.error("CLERK_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=500, detail="Webhook not configured")

    if not _verify_svix(payload, svix_id, svix_timestamp, svix_signature, settings.clerk_webhook_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    try:
        if abs(time.time() - int(svix_timestamp)) > 300:
            raise HTTPException(status_code=400, detail="Webhook too old")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timestamp")

    event = await request.json()
    event_type: str = event.get("type", "")
    data: dict = event.get("data", {})

    handlers = {
        "user.created": _on_user_created,
        "user.updated": _on_user_updated,
        "user.deleted": _on_user_deleted,
    }

    handler = handlers.get(event_type)
    if handler:
        await handler(data, db)
    else:
        logger.debug("Unhandled Clerk event: %s", event_type)

    return {"ok": True}


async def _on_user_created(data: dict, db: AsyncSession) -> None:
    clerk_id = data.get("id")
    if not clerk_id:
        return

    existing = await db.execute(select(User).where(User.clerk_user_id == clerk_id))
    if existing.scalar_one_or_none():
        return  # idempotent

    emails = data.get("email_addresses", [])
    primary_id = data.get("primary_email_address_id")
    email = next((e["email_address"] for e in emails if e.get("id") == primary_id), "")
    if not email and emails:
        email = emails[0].get("email_address", "")

    full_name = " ".join(filter(None, [data.get("first_name", ""), data.get("last_name", "")])).strip() or None

    await ensure_pending_clinic(db)

    user = User(
        clinic_id=PENDING_CLINIC_ID,
        clerk_user_id=clerk_id,
        email=email,
        full_name=full_name,
        password_hash="",
        role=UserRole.RECEPTIONIST,
    )
    db.add(user)
    try:
        await db.commit()
        logger.info("Created user for Clerk %s (%s)", clerk_id, email)
    except Exception:
        await db.rollback()
        logger.exception("Failed to create user for Clerk %s", clerk_id)


async def _on_user_updated(data: dict, db: AsyncSession) -> None:
    clerk_id = data.get("id")
    result = await db.execute(select(User).where(User.clerk_user_id == clerk_id, User.is_deleted.is_(False)))
    user = result.scalar_one_or_none()
    if not user:
        return

    emails = data.get("email_addresses", [])
    primary_id = data.get("primary_email_address_id")
    for e in emails:
        if e.get("id") == primary_id:
            user.email = e.get("email_address", user.email)
            break

    name = " ".join(filter(None, [data.get("first_name", ""), data.get("last_name", "")])).strip()
    if name:
        user.full_name = name

    await db.commit()


async def _on_user_deleted(data: dict, db: AsyncSession) -> None:
    clerk_id = data.get("id")
    result = await db.execute(select(User).where(User.clerk_user_id == clerk_id))
    user = result.scalar_one_or_none()
    if user:
        user.is_deleted = True
        await db.commit()
