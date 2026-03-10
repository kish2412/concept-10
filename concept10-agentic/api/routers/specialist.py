from fastapi import APIRouter

router = APIRouter()


@router.get("/ping")
async def ping_specialist() -> dict[str, str]:
    return {"status": "specialist_ok"}
