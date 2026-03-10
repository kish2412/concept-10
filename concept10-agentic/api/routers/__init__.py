from fastapi import APIRouter

from agents.registry.api import router as agents_registry_router
from api.routers.orchestrator import router as orchestrator_router
from api.routers.specialist import router as specialist_router
from api.routers.utility import router as utility_router

router = APIRouter()
router.include_router(agents_registry_router)
router.include_router(orchestrator_router, prefix="/orchestrator", tags=["orchestrator"])
router.include_router(utility_router, prefix="/utility", tags=["utility"])
router.include_router(specialist_router, prefix="/specialist", tags=["specialist"])
