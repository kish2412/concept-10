from fastapi import APIRouter

from app.api.v1.routes import auth, clinics, patients

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(clinics.router, prefix="/clinics", tags=["clinics"])
api_router.include_router(patients.router, prefix="/patients", tags=["patients"])
