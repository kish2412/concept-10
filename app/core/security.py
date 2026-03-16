"""app/core/security.py"""
import logging
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import httpx
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger("app.security")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password ──────────────────────────────────────────────────────────

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# ── Own HS256 JWT (local dev / admin bootstrap) ───────────────────────

def create_access_token(user_id: str, clinic_id: str, role: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {
        "sub": user_id,
        "clinic_id": clinic_id,
        "role": role,
        "exp": expire,
        "iss": "concept10-internal",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_internal_token(token: str) -> dict:
    """Decode own HS256 token. Raises ValueError on failure."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc


# ── Clerk RS256 JWT ───────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _fetch_clerk_jwks() -> dict:
    """
    Fetch Clerk's JWKS once per process lifecycle.
    Invalidate by restarting the server (Railway auto-restart handles this).
    """
    if not settings.clerk_jwks_url:
        raise ValueError("CLERK_JWKS_URL is not set in .env")
    resp = httpx.get(settings.clerk_jwks_url, timeout=5.0)
    resp.raise_for_status()
    return resp.json()


def decode_clerk_token(token: str) -> dict:
    """
    Verify and decode a Clerk-issued RS256 JWT.
    Returns payload containing at least {"sub": "<clerk_user_id>"}.
    Raises ValueError on any failure.
    """
    try:
        jwks = _fetch_clerk_jwks()
        payload = jwt.decode(token, jwks, algorithms=["RS256"], options={"verify_aud": False})
        if not payload.get("sub"):
            raise ValueError("Missing 'sub' claim in Clerk token")
        return payload
    except ExpiredSignatureError as exc:
        raise ValueError("Clerk token has expired") from exc
    except JWTError as exc:
        raise ValueError(f"Invalid Clerk token: {exc}") from exc


def is_clerk_token(token: str) -> bool:
    """True if the token header declares RS256 (Clerk). False for HS256 (own)."""
    try:
        return jwt.get_unverified_header(token).get("alg", "").upper() == "RS256"
    except Exception:
        return False
