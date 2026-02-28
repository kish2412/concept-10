from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.models.user import User


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def build_access_token(user_id: str, clinic_id: str) -> str:
    return create_access_token(subject=user_id, clinic_id=clinic_id)
