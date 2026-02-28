from fastapi import APIRouter, Depends

from app.api.deps import get_current_tenant_id, get_current_user_id

router = APIRouter()


@router.get("/me")
async def clinic_context(
    clinic_id: str = Depends(get_current_tenant_id),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    return {"clinic_id": clinic_id, "user_id": user_id}
