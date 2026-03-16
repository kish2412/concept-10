"""
app/api/v1/routes/auth.py
──────────────────────────
Local login (dev / admin bootstrap).
Clerk-authenticated users don't use this endpoint —
they sign in via Clerk and their JWT is verified in AuthMiddleware.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.schemas.auth import LoginRequest, TokenResponse
from sqlalchemy import select
from app.models.user import User

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(
        select(User).where(User.email == payload.email, User.is_deleted.is_(False))
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(
        user_id=str(user.id),
        clinic_id=str(user.clinic_id),
        role=user.role.value,
    )
    return TokenResponse(access_token=token)
