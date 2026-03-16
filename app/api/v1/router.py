"""app/api/v1/router.py"""
from fastapi import APIRouter

from app.api.v1.routes import (
    auth,
    clinics,
    encounters,
    lookup,
    me,
    patients,
    roles,
    tenants,
    visit_flow,
    webhooks,
)

api_router = APIRouter()

# ── Public / auth ─────────────────────────────────────────────────────
api_router.include_router(auth.router,       prefix="/auth",       tags=["auth"])
api_router.include_router(webhooks.router,   prefix="/webhooks",   tags=["webhooks"])

# ── Current user ──────────────────────────────────────────────────────
api_router.include_router(me.router,         prefix="/me",         tags=["me"])

# ── Tenant management ─────────────────────────────────────────────────
api_router.include_router(tenants.router,    prefix="/tenants",    tags=["tenants"])

# ── RBAC ──────────────────────────────────────────────────────────────
api_router.include_router(roles.router,      prefix="/roles",      tags=["roles"])
api_router.include_router(visit_flow.router, prefix="/visit-flow", tags=["visit-flow"])

# ── Clinical ──────────────────────────────────────────────────────────
api_router.include_router(clinics.router,    prefix="/clinics",    tags=["clinics"])
api_router.include_router(patients.router,   prefix="/patients",   tags=["patients"])
api_router.include_router(encounters.router, prefix="/encounters", tags=["encounters"])
api_router.include_router(lookup.router,     prefix="/lookup",     tags=["lookup"])
