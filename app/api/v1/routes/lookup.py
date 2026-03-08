from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_tenant_id
from app.core.rbac import authorize_role

router = APIRouter()

# Minimal starter catalogs for autocomplete. Replace with DB-backed catalogs later.
ICD10_CATALOG = [
    {"code": "J06.9", "description": "Acute upper respiratory infection, unspecified"},
    {"code": "I10", "description": "Essential (primary) hypertension"},
    {"code": "E11.9", "description": "Type 2 diabetes mellitus without complications"},
    {"code": "M54.5", "description": "Low back pain"},
    {"code": "R51.9", "description": "Headache, unspecified"},
]

DRUG_CATALOG = [
    {
        "code": "RX-ASPIRIN-81",
        "name": "Aspirin",
        "generic_name": "Acetylsalicylic acid",
        "interactions": ["Warfarin", "Ibuprofen"],
        "is_controlled": False,
    },
    {
        "code": "RX-AMOX-500",
        "name": "Amoxicillin",
        "generic_name": "Amoxicillin",
        "interactions": ["Methotrexate"],
        "is_controlled": False,
    },
    {
        "code": "RX-OXY-5",
        "name": "Oxycodone",
        "generic_name": "Oxycodone",
        "interactions": ["Diazepam", "Alcohol"],
        "is_controlled": True,
    },
    {
        "code": "RX-METF-500",
        "name": "Metformin",
        "generic_name": "Metformin",
        "interactions": ["Alcohol"],
        "is_controlled": False,
    },
]


@router.get(
    "/icd10",
    dependencies=[
        Depends(get_current_tenant_id),
        Depends(authorize_role("admin", "provider", "nurse", "viewer")),
    ],
)
async def search_icd10(q: str = Query(..., min_length=1)) -> list[dict[str, str]]:
    needle = q.strip().lower()
    return [
        row
        for row in ICD10_CATALOG
        if needle in row["code"].lower() or needle in row["description"].lower()
    ][:20]


@router.get(
    "/drugs",
    dependencies=[
        Depends(get_current_tenant_id),
        Depends(authorize_role("admin", "provider", "nurse", "viewer")),
    ],
)
async def search_drugs(q: str = Query(..., min_length=1)) -> list[dict]:
    needle = q.strip().lower()
    return [
        row
        for row in DRUG_CATALOG
        if needle in row["name"].lower() or needle in row["generic_name"].lower()
    ][:20]
