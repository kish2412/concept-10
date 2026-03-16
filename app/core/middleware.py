"""
app/core/middleware.py
──────────────────────
Single unified auth middleware. Supports:
  1. Clerk RS256 JWT  → verify → DB lookup by clerk_user_id → get role + clinic_id
  2. Own HS256 JWT    → verify → sub=user_id, clinic_id, role all in payload
  3. Dev headers      → x-clinic-id + x-user-role (development environment only)

Sets on request.state:
  user_id   — str(UUID) of users.id
  clinic_id — str(UUID) of clinics.id
  user_role — UserRole enum value string
"""
import logging
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.onboarding import PENDING_CLINIC_ID, ensure_pending_clinic
from app.core.security import decode_internal_token, decode_clerk_token, is_clerk_token
from app.core.tenant_context import set_current_tenant
from app.models.user import User, UserRole

logger = logging.getLogger("app.auth")

PUBLIC_PATHS = {
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/webhooks/clerk",
}


class AuthMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")

        if authorization.startswith("Bearer "):
            token = authorization.removeprefix("Bearer ").strip()
            user_id, clinic_id, role = await self._resolve_token(token)
        elif settings.environment == "development":
            user_id, clinic_id, role = self._resolve_dev_headers(request)
        else:
            return JSONResponse(status_code=401, content={"detail": "Authorization header required"})

        if not user_id or not clinic_id:
            return JSONResponse(status_code=401, content={"detail": "Authentication failed"})

        request.state.user_id = user_id
        request.state.clinic_id = clinic_id
        request.state.user_role = role
        set_current_tenant(clinic_id)

        if settings.tenant_auth_log_success:
            logger.info("auth ok | user=%s clinic=%s role=%s path=%s", user_id, clinic_id, role, request.url.path)

        return await call_next(request)

    # ── Token resolution ──────────────────────────────────────────────

    async def _resolve_token(self, token: str) -> tuple[str | None, str | None, str]:
        if is_clerk_token(token):
            return await self._resolve_clerk(token)
        return self._resolve_internal(token)

    def _resolve_internal(self, token: str) -> tuple[str | None, str | None, str]:
        try:
            payload = decode_internal_token(token)
            user_id = payload.get("sub")
            clinic_id = payload.get("clinic_id")
            role = payload.get("role", "receptionist")
            if not user_id or not clinic_id:
                return None, None, "receptionist"
            return user_id, clinic_id, role
        except ValueError as exc:
            logger.debug("Internal token decode failed: %s", exc)
            return None, None, "receptionist"

    async def _resolve_clerk(self, token: str) -> tuple[str | None, str | None, str]:
        try:
            payload = decode_clerk_token(token)
            clerk_user_id: str = payload["sub"]
        except ValueError as exc:
            logger.warning("Clerk token invalid: %s", exc)
            return None, None, "receptionist"

        try:
            async with SessionLocal() as session:
                result = await session.execute(
                    select(User.id, User.clinic_id, User.role).where(
                        User.clerk_user_id == clerk_user_id,
                        User.is_deleted.is_(False),
                    )
                )
                row = result.one_or_none()

                if not row:
                    # Provision user on the fly (useful in dev when webhooks aren't configured)
                    user = await self._provision_clerk_user(session, clerk_user_id)
                    if user:
                        return str(user.id), str(user.clinic_id), user.role.value

                    logger.warning("Clerk user %s not found in DB (not onboarded)", clerk_user_id)
                    return None, None, "receptionist"

                return str(row.id), str(row.clinic_id), row.role.value

        except Exception as exc:
            logger.exception("DB lookup for Clerk user failed", exc_info=exc)
            return None, None, "receptionist"

    async def _provision_clerk_user(self, session: AsyncSession, clerk_user_id: str) -> User | None:
        if not settings.clerk_secret_key:
            logger.warning("CLERK_SECRET_KEY missing; cannot provision Clerk user %s", clerk_user_id)
            return None

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"https://api.clerk.com/v1/users/{clerk_user_id}",
                    headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
                )
            if not resp.is_success:
                logger.warning("Failed to fetch Clerk user %s: %s", clerk_user_id, resp.text)
                return None
            data = resp.json()
        except Exception as exc:
            logger.warning("Clerk user fetch failed: %s", exc)
            return None

        emails = data.get("email_addresses", [])
        primary_id = data.get("primary_email_address_id")
        email = next((e.get("email_address") for e in emails if e.get("id") == primary_id), "")
        if not email and emails:
            email = emails[0].get("email_address", "")
        if not email:
            if settings.environment == "development":
                email = f"{clerk_user_id}@local.clerk"
                logger.warning(
                    "Clerk user %s has no email; using placeholder %s (dev only)",
                    clerk_user_id, email,
                )
            else:
                logger.warning("Clerk user %s has no email; cannot provision", clerk_user_id)
                return None

        full_name = " ".join(filter(None, [data.get("first_name", ""), data.get("last_name", "")])).strip() or None

        # If user already exists (race or prior stub), reuse/update it.
        existing = await session.execute(
            select(User).where(User.clerk_user_id == clerk_user_id, User.is_deleted.is_(False))
        )
        user = existing.scalar_one_or_none()
        if user:
            return user

        by_email = await session.execute(
            select(User).where(User.email == email, User.is_deleted.is_(False))
        )
        user = by_email.scalar_one_or_none()
        if user and not user.clerk_user_id:
            user.clerk_user_id = clerk_user_id
            if not user.clinic_id:
                await ensure_pending_clinic(session)
                user.clinic_id = PENDING_CLINIC_ID
            if not user.role:
                user.role = UserRole.RECEPTIONIST
            if not user.full_name:
                user.full_name = full_name
            try:
                await session.commit()
                await session.refresh(user)
                logger.info("Linked Clerk user %s to existing user %s", clerk_user_id, user.id)
                return user
            except Exception:
                await session.rollback()
                logger.exception("Failed to link Clerk user %s to existing email", clerk_user_id)
                return None

        await ensure_pending_clinic(session)
        user = User(
            clinic_id=PENDING_CLINIC_ID,
            clerk_user_id=clerk_user_id,
            email=email,
            full_name=full_name,
            password_hash="",
            role=UserRole.RECEPTIONIST,
        )
        session.add(user)
        try:
            await session.commit()
            await session.refresh(user)
            logger.info("Provisioned Clerk user %s (%s)", clerk_user_id, email)
            return user
        except IntegrityError as exc:
            await session.rollback()
            logger.warning(
                "Provisioning Clerk user %s hit IntegrityError; retrying lookup: %s",
                clerk_user_id,
                getattr(exc, "orig", exc),
            )
            # Another process created the user; try read again
            result = await session.execute(
                select(User).where(User.clerk_user_id == clerk_user_id, User.is_deleted.is_(False))
            )
            return result.scalar_one_or_none()
        except Exception:
            await session.rollback()
            logger.exception("Failed to provision Clerk user %s", clerk_user_id)
            return None

    # ── Dev headers fallback ──────────────────────────────────────────

    def _resolve_dev_headers(self, request: Request) -> tuple[str | None, str | None, str]:
        clinic_id = request.headers.get("x-clinic-id") or request.headers.get("clinic_id")
        user_id = request.headers.get("x-user-id", "00000000-0000-0000-0000-000000000001")
        role = request.headers.get("x-user-role", "admin")
        if not clinic_id:
            return None, None, role
        try:
            uuid.UUID(clinic_id)
            return user_id, clinic_id, role
        except ValueError:
            return None, None, role
