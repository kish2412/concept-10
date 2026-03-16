"""
app/seeds/rbac_seed.py
───────────────────────
Run once after migration to seed the permission matrix and
create default VisitFlowConfig for existing clinics.

Usage:
    python -m app.seeds.rbac_seed
"""
import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.rbac import Permission, PermissionAction, PermissionResource, RolePermission
from app.models.visit_flow import (
    DEFAULT_STATE_ORDER, DEFAULT_TRANSITION_ROLES,
    MANDATORY_STATES, OPTIONAL_STATES,
    VisitFlowConfig, VisitStateConfig, VisitTransitionRule, VisitStatus,
)

A = PermissionAction
R = PermissionResource

ROLE_PERMISSIONS: dict[str, list[tuple[PermissionAction, PermissionResource]]] = {
    "admin": [
        (A.CREATE, R.USER_MANAGEMENT), (A.READ, R.USER_MANAGEMENT),
        (A.UPDATE, R.USER_MANAGEMENT), (A.DELETE, R.USER_MANAGEMENT),
        (A.CREATE, R.CLINIC_SETTINGS), (A.READ, R.CLINIC_SETTINGS), (A.UPDATE, R.CLINIC_SETTINGS),
        (A.READ,   R.REPORTS),
        (A.READ,   R.AUDIT_LOGS),
        (A.CREATE, R.FEE_TEMPLATE), (A.READ, R.FEE_TEMPLATE), (A.UPDATE, R.FEE_TEMPLATE),
        (A.READ,   R.QUEUE),   (A.UPDATE, R.QUEUE),
        (A.READ,   R.APPOINTMENT), (A.UPDATE, R.APPOINTMENT),
        (A.READ,   R.PATIENT),
        (A.READ,   R.INVOICE),
        (A.CREATE, R.PAYMENT), (A.READ, R.PAYMENT),
        (A.CREATE, R.CHECKIN), (A.UPDATE, R.CHECKIN),
    ],
    "receptionist": [
        (A.CREATE, R.PATIENT),  (A.READ, R.PATIENT),  (A.UPDATE, R.PATIENT),
        (A.CREATE, R.CHECKIN),  (A.UPDATE, R.CHECKIN),
        (A.READ,   R.QUEUE),    (A.UPDATE, R.QUEUE),
        (A.CREATE, R.APPOINTMENT), (A.READ, R.APPOINTMENT), (A.UPDATE, R.APPOINTMENT),
        (A.CREATE, R.CHIEF_COMPLAINT), (A.UPDATE, R.CHIEF_COMPLAINT),
        (A.READ,   R.INVOICE),
        (A.CREATE, R.PAYMENT),  (A.READ, R.PAYMENT),
    ],
    "nurse": [
        (A.READ,   R.PATIENT),
        (A.READ,   R.QUEUE),    (A.UPDATE, R.QUEUE),
        (A.CREATE, R.VITALS),   (A.READ, R.VITALS),   (A.UPDATE, R.VITALS),
        (A.CREATE, R.NURSING_NOTES), (A.READ, R.NURSING_NOTES), (A.UPDATE, R.NURSING_NOTES),
        (A.READ,   R.CHIEF_COMPLAINT),
        (A.READ,   R.PRESCRIPTION),
        (A.UPDATE, R.CHECKIN),
    ],
    "doctor": [
        (A.READ,   R.PATIENT),  (A.UPDATE, R.PATIENT),
        (A.READ,   R.PATIENT_HISTORY),
        (A.READ,   R.CHIEF_COMPLAINT),
        (A.READ,   R.VITALS),
        (A.CREATE, R.CLINICAL_NOTES), (A.READ, R.CLINICAL_NOTES), (A.UPDATE, R.CLINICAL_NOTES),
        (A.CREATE, R.PRESCRIPTION),   (A.READ, R.PRESCRIPTION),   (A.UPDATE, R.PRESCRIPTION),
        (A.CREATE, R.INVESTIGATION),  (A.READ, R.INVESTIGATION),  (A.UPDATE, R.INVESTIGATION),
        (A.READ,   R.NURSING_NOTES),
        (A.READ,   R.QUEUE),   (A.UPDATE, R.QUEUE),
        (A.READ,   R.APPOINTMENT),
        (A.READ,   R.REPORTS),
    ],
    "consultant": [
        (A.READ,   R.PATIENT),
        (A.READ,   R.PATIENT_HISTORY),
        (A.READ,   R.CHIEF_COMPLAINT),
        (A.READ,   R.VITALS),
        (A.CREATE, R.CLINICAL_NOTES), (A.READ, R.CLINICAL_NOTES), (A.UPDATE, R.CLINICAL_NOTES),
        (A.CREATE, R.PRESCRIPTION),   (A.READ, R.PRESCRIPTION),   (A.UPDATE, R.PRESCRIPTION),
        (A.CREATE, R.INVESTIGATION),  (A.READ, R.INVESTIGATION),
        (A.READ,   R.NURSING_NOTES),
        (A.READ,   R.QUEUE),
    ],
    "billing": [
        (A.READ,   R.PATIENT),
        (A.CREATE, R.INVOICE),  (A.READ, R.INVOICE),  (A.UPDATE, R.INVOICE),
        (A.CREATE, R.PAYMENT),  (A.READ, R.PAYMENT),  (A.UPDATE, R.PAYMENT),
        (A.READ,   R.FEE_TEMPLATE),
        (A.READ,   R.REPORTS),
    ],
}


async def seed_permissions(db: AsyncSession) -> None:
    print("Seeding system permissions...")
    all_perms: dict[tuple, Permission] = {}

    existing = await db.execute(select(Permission))
    for perm in existing.scalars().all():
        all_perms[(perm.action, perm.resource)] = perm

    for role_perms in ROLE_PERMISSIONS.values():
        for action, resource in role_perms:
            key = (action, resource)
            if key not in all_perms:
                p = Permission(action=action, resource=resource)
                db.add(p)
                all_perms[key] = p

    await db.flush()

    existing_rp = await db.execute(select(RolePermission.role, RolePermission.permission_id))
    existing_pairs = {(r, pid) for r, pid in existing_rp.all()}

    for role, role_perms in ROLE_PERMISSIONS.items():
        for action, resource in role_perms:
            perm_id = all_perms[(action, resource)].id
            key = (role, perm_id)
            if key in existing_pairs:
                continue
            db.add(RolePermission(role=role, permission_id=perm_id))

    await db.commit()
    print(f"  OK {len(all_perms)} permissions across {len(ROLE_PERMISSIONS)} roles")


async def seed_visit_flow_for_clinic(clinic_id: uuid.UUID, db: AsyncSession) -> None:
    """Create default VisitFlowConfig for a clinic. Idempotent."""
    exists = await db.scalar(select(VisitFlowConfig.id).where(VisitFlowConfig.clinic_id == clinic_id))
    if exists:
        return

    config = VisitFlowConfig(clinic_id=clinic_id, last_modified_by="seed")
    db.add(config)
    await db.flush()

    all_states = list(MANDATORY_STATES) + list(OPTIONAL_STATES) + [VisitStatus.CANCELLED, VisitStatus.NO_SHOW]
    for state in all_states:
        db.add(VisitStateConfig(
            flow_config_id=config.id,
            state=state.value,
            is_active=True,
            is_mandatory=(state in MANDATORY_STATES),
            display_label=state.name.replace("_", " ").title(),
            order_index=DEFAULT_STATE_ORDER.get(state, 500),
        ))

    for (from_s, to_s), roles in DEFAULT_TRANSITION_ROLES.items():
        db.add(VisitTransitionRule(
            flow_config_id=config.id,
            from_state=from_s.value,
            to_state=to_s.value,
            allowed_roles=roles,
            created_by="seed",
        ))

    await db.commit()
    print(f"  OK VisitFlowConfig seeded for clinic {clinic_id}")


async def seed_all_clinic_flows(db: AsyncSession) -> None:
    from app.models.clinic import Clinic
    result = await db.execute(select(Clinic.id).where(Clinic.is_deleted.is_(False)))
    ids = result.scalars().all()
    print(f"Seeding visit flow for {len(ids)} clinic(s)...")
    for clinic_id in ids:
        await seed_visit_flow_for_clinic(clinic_id, db)


async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as db:
        await seed_permissions(db)
        await seed_all_clinic_flows(db)
    await engine.dispose()
    print("Seed complete OK")


if __name__ == "__main__":
    asyncio.run(main())
