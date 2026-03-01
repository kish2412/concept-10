import uuid

from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.database import SessionLocal
from app.models.clinic import Clinic
from app.core.security import decode_token
from app.core.tenant_context import set_current_tenant


class TenantJWTMiddleware(BaseHTTPMiddleware):
    public_paths = {
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",
        "/",
    }

    @staticmethod
    async def _resolve_tenant_clinic_id(raw_tenant: str) -> str | None:
        try:
            parsed_uuid = uuid.UUID(raw_tenant)
            return str(parsed_uuid)
        except ValueError:
            pass

        try:
            async with SessionLocal() as session:
                result = await session.execute(
                    select(Clinic.id).where(Clinic.external_org_id == raw_tenant, Clinic.is_deleted.is_(False))
                )
                clinic_id = result.scalar_one_or_none()
                return str(clinic_id) if clinic_id else None
        except BaseException:
            return None

    @classmethod
    async def _extract_header_context(cls, request: Request) -> tuple[str | None, str | None]:
        raw_tenant = request.headers.get("x-clinic-id") or request.headers.get("clinic_id")
        user_id = request.headers.get("x-user-id")
        if not raw_tenant:
            return None, None

        try:
            clinic_id = await cls._resolve_tenant_clinic_id(raw_tenant)
        except BaseException:
            return None, None
        if not clinic_id:
            return None, None

        return user_id or "external_user", clinic_id

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        if request.url.path in self.public_paths:
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        user_id = None
        clinic_id = None

        if authorization.startswith("Bearer "):
            token = authorization.removeprefix("Bearer ").strip()
            try:
                payload = decode_token(token)
                user_id = payload.get("sub")
                clinic_id = payload.get("clinic_id")
                if not user_id or not clinic_id:
                    raise ValueError("Token missing required claims")
            except ValueError:
                user_id, clinic_id = await self._extract_header_context(request)
        else:
            user_id, clinic_id = await self._extract_header_context(request)

        if not user_id or not clinic_id:
            return JSONResponse(status_code=401, content={"detail": "Missing tenant authentication context"})

        request.state.user_id = user_id
        request.state.clinic_id = clinic_id
        set_current_tenant(clinic_id)

        return await call_next(request)
