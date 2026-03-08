"""Role-based access control dependency for FastAPI routes."""

from fastapi import Depends, HTTPException, Request, status


def get_current_user_role(request: Request) -> str:
    """Extract user role from request state (set by TenantJWTMiddleware)."""
    return getattr(request.state, "user_role", "provider")


def authorize_role(*allowed_roles: str):
    """
    FastAPI dependency that restricts access to users whose role
    is in the *allowed_roles* set.

    Usage::

        @router.post("", dependencies=[Depends(authorize_role("admin", "provider"))])
        async def create_something(...): ...
    """
    def _guard(role: str = Depends(get_current_user_role)) -> str:
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' is not permitted for this action",
            )
        return role

    return _guard
