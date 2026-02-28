import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

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
    def _extract_header_context(request: Request) -> tuple[str | None, str | None]:
        clinic_id = request.headers.get("clinic_id") or request.headers.get("x-clinic-id")
        user_id = request.headers.get("x-user-id")
        if not clinic_id:
            return None, None

        try:
            uuid.UUID(clinic_id)
        except ValueError:
            return None, None

        return user_id or "external_user", clinic_id

    async def dispatch(self, request: Request, call_next):
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
                user_id, clinic_id = self._extract_header_context(request)
        else:
            user_id, clinic_id = self._extract_header_context(request)

        if not user_id or not clinic_id:
            return JSONResponse(status_code=401, content={"detail": "Missing tenant authentication context"})

        request.state.user_id = user_id
        request.state.clinic_id = clinic_id
        set_current_tenant(clinic_id)

        return await call_next(request)
