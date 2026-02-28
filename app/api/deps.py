from fastapi import Depends, HTTPException, Request, status


def get_current_tenant_id(request: Request) -> str:
    clinic_id = getattr(request.state, "clinic_id", None)
    if not clinic_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing tenant context")
    return clinic_id


def get_current_user_id(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing user context")
    return user_id


TenantIdDep = Depends(get_current_tenant_id)
UserIdDep = Depends(get_current_user_id)
