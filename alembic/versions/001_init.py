"""
Fresh init migration — replaces ALL existing migrations.

Since nothing is in production:
  1. Drop your Supabase DB schema (or run: alembic downgrade base)
  2. Delete all files in alembic/versions/
  3. Copy this file to alembic/versions/001_init.py
  4. Run: alembic upgrade head
  5. Run: python -m app.seeds.rbac_seed

Revision ID: 001_init
Revises:
Create Date: 2026-03-16
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ── Enums ─────────────────────────────────────────────────────────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE userrole AS ENUM
                ('admin','receptionist','nurse','doctor','consultant','billing');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE permissionaction AS ENUM ('create','read','update','delete');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE permissionresource AS ENUM (
                'patient','patient_history','clinical_notes','chief_complaint',
                'vitals','prescription','investigation','nursing_notes',
                'queue','appointment','checkin',
                'user_management','clinic_settings','reports','audit_logs',
                'invoice','payment','fee_template'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)

    # ── clinics ───────────────────────────────────────────────────────
    op.create_table(
        "clinics",
        sa.Column("id",               sa.UUID(),       nullable=False),
        sa.Column("clinic_id",        sa.UUID(),       nullable=False),
        sa.Column("name",             sa.String(255),  nullable=False),
        sa.Column("slug",             sa.String(100),  nullable=True),
        sa.Column("external_org_id",  sa.String(255),  nullable=True),
        sa.Column("is_active",        sa.Boolean(),    nullable=False, server_default="true"),
        sa.Column("ai_enabled",       sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column("ai_policy_tier",   sa.String(50),   nullable=True),
        sa.Column("ai_guardrail_profile", sa.String(100), nullable=True),
        sa.Column("allow_custom_roles", sa.Boolean(),  nullable=False, server_default="false"),
        sa.Column("max_custom_roles", sa.Integer(),    nullable=False, server_default="5"),
        sa.Column("created_at",       sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",       sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted",       sa.Boolean(),    nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id", name="pk_clinics"),
        sa.UniqueConstraint("slug",          name="uq_clinics_slug"),
        sa.UniqueConstraint("external_org_id", name="uq_clinics_external_org_id"),
    )
    op.create_index("ix_clinics_clinic_id",      "clinics", ["clinic_id"])
    op.create_index("ix_clinics_external_org_id","clinics", ["external_org_id"], unique=True)

    # ── users ─────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id",             sa.UUID(),      nullable=False),
        sa.Column("clinic_id",      sa.UUID(),      nullable=False),
        sa.Column("clerk_user_id",  sa.String(128), nullable=True),
        sa.Column("email",          sa.String(320), nullable=False),
        sa.Column("full_name",      sa.String(200), nullable=True),
        sa.Column("phone",          sa.String(30),  nullable=True),
        sa.Column("department",     sa.String(100), nullable=True),
        sa.Column("specialisation", sa.String(100), nullable=True),
        sa.Column("password_hash",  sa.String(255), nullable=False, server_default=""),
        sa.Column("role",
            postgresql.ENUM(
                "admin","receptionist","nurse","doctor","consultant","billing",
                name="userrole", create_type=False,
            ),
            nullable=False, server_default="receptionist"),
        sa.Column("created_at",  sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",  sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted",  sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE", name="fk_users_clinic_id_clinics"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email",         name="uq_users_email"),
        sa.UniqueConstraint("clerk_user_id", name="uq_users_clerk_user_id"),
    )
    op.create_index("ix_users_clinic_id",     "users", ["clinic_id"])
    op.create_index("ix_users_email",         "users", ["email"], unique=True)
    op.create_index("ix_users_clerk_user_id", "users", ["clerk_user_id"])

    # ── patients ──────────────────────────────────────────────────────
    op.create_table(
        "patients",
        sa.Column("id",            sa.UUID(),       nullable=False),
        sa.Column("clinic_id",     sa.UUID(),       nullable=False),
        sa.Column("first_name",    sa.String(100),  nullable=False),
        sa.Column("last_name",     sa.String(100),  nullable=False),
        sa.Column("date_of_birth", sa.Date(),       nullable=False),
        sa.Column("gender",        sa.String(50),   nullable=False),
        sa.Column("phone",         sa.String(30),   nullable=True),
        sa.Column("email",         sa.String(320),  nullable=True),
        sa.Column("address",       sa.String(500),  nullable=True),
        sa.Column("blood_type",    sa.String(10),   nullable=True),
        sa.Column("allergies",     postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("is_active",     sa.Boolean(),    nullable=False, server_default="true"),
        sa.Column("created_at",    sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",    sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted",    sa.Boolean(),    nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE", name="fk_patients_clinic_id_clinics"),
        sa.PrimaryKeyConstraint("id", name="pk_patients"),
    )
    op.create_index("ix_patients_clinic_id", "patients", ["clinic_id"])
    op.create_index("ix_patients_email",     "patients", ["email"])

    # ── patient_backgrounds ───────────────────────────────────────────
    op.create_table(
        "patient_backgrounds",
        sa.Column("id",                  sa.UUID(), nullable=False),
        sa.Column("clinic_id",           sa.UUID(), nullable=False),
        sa.Column("patient_id",          sa.UUID(), nullable=False),
        sa.Column("medical_history",     sa.Text(), nullable=True),
        sa.Column("surgical_history",    sa.Text(), nullable=True),
        sa.Column("family_history",      sa.Text(), nullable=True),
        sa.Column("social_history",      sa.Text(), nullable=True),
        sa.Column("current_medications", sa.Text(), nullable=True),
        sa.Column("immunizations",       postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["clinic_id"],  ["clinics.id"],  ondelete="CASCADE", name="fk_patient_backgrounds_clinic_id_clinics"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE", name="fk_patient_backgrounds_patient_id_patients"),
        sa.PrimaryKeyConstraint("id", name="pk_patient_backgrounds"),
    )
    op.create_index("ix_patient_backgrounds_clinic_id",  "patient_backgrounds", ["clinic_id"])
    op.create_index("ix_patient_backgrounds_patient_id", "patient_backgrounds", ["patient_id"], unique=True)

    # ── encounters ────────────────────────────────────────────────────
    op.create_table(
        "encounters",
        sa.Column("id",             sa.UUID(),      nullable=False),
        sa.Column("clinic_id",      sa.UUID(),      nullable=False),
        sa.Column("encounter_id",   sa.String(30),  nullable=False),
        sa.Column("patient_id",     sa.UUID(),      nullable=False),
        sa.Column("provider_id",    sa.UUID(),      nullable=True),
        sa.Column("facility_id",    sa.UUID(),      nullable=True),
        sa.Column("department_id",  sa.UUID(),      nullable=True),
        sa.Column("encounter_type", sa.String(50),  nullable=False, server_default="CONSULTATION"),
        sa.Column("status",         sa.String(50),  nullable=False, server_default="REGISTERED"),
        sa.Column("chief_complaint",sa.Text(),      nullable=True),
        sa.Column("ai_triage_summary",        sa.Text(),   nullable=True),
        sa.Column("ai_triage_focus_points",   postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ai_triage_red_flags",      postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ai_triage_missing_information", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ai_triage_generated_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_triage_orchestration",  sa.String(120), nullable=True),
        sa.Column("ai_triage_model_provider", sa.String(80),  nullable=True),
        sa.Column("ai_triage_model_name",     sa.String(120), nullable=True),
        sa.Column("ai_triage_guardrail_profile", sa.String(100), nullable=True),
        sa.Column("triage_assessment",        postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("scheduled_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("checked_in_at",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("triage_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by",     sa.UUID(), nullable=True),
        sa.Column("updated_by",     sa.UUID(), nullable=True),
        sa.Column("deleted_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",     sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",     sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted",     sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["clinic_id"],  ["clinics.id"],  ondelete="CASCADE", name="fk_encounters_clinic_id_clinics"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE", name="fk_encounters_patient_id_patients"),
        sa.PrimaryKeyConstraint("id", name="pk_encounters"),
        sa.UniqueConstraint("encounter_id", name="uq_encounters_encounter_id"),
    )
    op.create_index("ix_encounters_clinic_id",   "encounters", ["clinic_id"])
    op.create_index("ix_encounters_patient_id",  "encounters", ["patient_id"])
    op.create_index("ix_encounters_status",      "encounters", ["status"])
    op.create_index("ix_encounters_scheduled_at","encounters", ["scheduled_at"])

    # ── encounter sub-tables (vitals, notes, diagnoses, orders, medications, disposition) ──
    for table, cols in [
        ("encounter_vitals", [
            sa.Column("encounter_id",            sa.UUID(),           nullable=False),
            sa.Column("blood_pressure_systolic",  sa.Integer(),        nullable=True),
            sa.Column("blood_pressure_diastolic", sa.Integer(),        nullable=True),
            sa.Column("pulse_rate",               sa.Numeric(5,1),     nullable=True),
            sa.Column("respiratory_rate",         sa.Numeric(5,1),     nullable=True),
            sa.Column("temperature",              sa.Numeric(4,1),     nullable=True),
            sa.Column("oxygen_saturation",        sa.Numeric(5,2),     nullable=True),
            sa.Column("weight",                   sa.Numeric(6,2),     nullable=True),
            sa.Column("height",                   sa.Numeric(5,1),     nullable=True),
            sa.Column("bmi",                      sa.Numeric(5,2),     nullable=True),
            sa.Column("pain_score",               sa.Integer(),        nullable=True),
            sa.Column("recorded_by",              sa.UUID(),           nullable=True),
            sa.Column("recorded_at",              sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        ]),
        ("encounter_notes", [
            sa.Column("encounter_id",  sa.UUID(),      nullable=False),
            sa.Column("note_type",     sa.String(50),  nullable=False, server_default="SOAP"),
            sa.Column("subjective",    sa.Text(),      nullable=True),
            sa.Column("objective",     sa.Text(),      nullable=True),
            sa.Column("assessment",    sa.Text(),      nullable=True),
            sa.Column("plan",          sa.Text(),      nullable=True),
            sa.Column("author_id",     sa.UUID(),      nullable=True),
            sa.Column("author_role",   sa.String(50),  nullable=True),
            sa.Column("is_signed",     sa.Boolean(),   nullable=False, server_default="false"),
            sa.Column("signed_at",     sa.DateTime(timezone=True), nullable=True),
            sa.Column("version",       sa.Integer(),   nullable=False, server_default="1"),
        ]),
        ("encounter_diagnoses", [
            sa.Column("encounter_id",         sa.UUID(),      nullable=False),
            sa.Column("icd_code",             sa.String(20),  nullable=False),
            sa.Column("icd_description",      sa.String(500), nullable=False),
            sa.Column("diagnosis_type",       sa.String(50),  nullable=False, server_default="PRIMARY"),
            sa.Column("onset_date",           sa.Date(),      nullable=True),
            sa.Column("is_chronic_condition", sa.Boolean(),   nullable=False, server_default="false"),
            sa.Column("added_by",             sa.UUID(),      nullable=True),
        ]),
        ("encounter_orders", [
            sa.Column("encounter_id",      sa.UUID(),      nullable=False),
            sa.Column("order_type",        sa.String(50),  nullable=False),
            sa.Column("order_code",        sa.String(50),  nullable=True),
            sa.Column("order_description", sa.String(500), nullable=False),
            sa.Column("status",            sa.String(50),  nullable=False, server_default="PENDING"),
            sa.Column("priority",          sa.String(50),  nullable=False, server_default="ROUTINE"),
            sa.Column("ordered_by",        sa.UUID(),      nullable=True),
            sa.Column("ordered_at",        sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
            sa.Column("result_summary",    sa.Text(),      nullable=True),
        ]),
        ("encounter_medications", [
            sa.Column("encounter_id",           sa.UUID(),      nullable=False),
            sa.Column("drug_code",              sa.String(50),  nullable=True),
            sa.Column("drug_name",              sa.String(255), nullable=False),
            sa.Column("generic_name",           sa.String(255), nullable=True),
            sa.Column("dosage",                 sa.String(100), nullable=False),
            sa.Column("dosage_unit",            sa.String(50),  nullable=False),
            sa.Column("frequency",              sa.String(100), nullable=False),
            sa.Column("route",                  sa.String(50),  nullable=False),
            sa.Column("duration_days",          sa.Integer(),   nullable=True),
            sa.Column("quantity",               sa.Integer(),   nullable=True),
            sa.Column("special_instructions",   sa.Text(),      nullable=True),
            sa.Column("is_controlled_substance",sa.Boolean(),   nullable=False, server_default="false"),
            sa.Column("prescribed_by",          sa.UUID(),      nullable=True),
            sa.Column("prescribed_at",          sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        ]),
    ]:
        standard = [
            sa.Column("id",        sa.UUID(), nullable=False),
            sa.Column("clinic_id", sa.UUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        ]
        op.create_table(
            table,
            *standard,
            *cols,
            sa.ForeignKeyConstraint(["clinic_id"],    ["clinics.id"],    ondelete="CASCADE", name=f"fk_{table}_clinic_id_clinics"),
            sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="CASCADE", name=f"fk_{table}_encounter_id_encounters"),
            sa.PrimaryKeyConstraint("id", name=f"pk_{table}"),
        )
        op.create_index(f"ix_{table}_clinic_id",    table, ["clinic_id"])
        op.create_index(f"ix_{table}_encounter_id", table, ["encounter_id"])

    # encounter_dispositions (has unique constraint on encounter_id)
    op.create_table(
        "encounter_dispositions",
        sa.Column("id",           sa.UUID(), nullable=False),
        sa.Column("clinic_id",    sa.UUID(), nullable=False),
        sa.Column("encounter_id", sa.UUID(), nullable=False),
        sa.Column("disposition_type",          sa.String(50),  nullable=False),
        sa.Column("follow_up_required",        sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("follow_up_in_days",         sa.Integer(),   nullable=True),
        sa.Column("discharge_instructions",    sa.Text(),      nullable=True),
        sa.Column("activity_restrictions",     sa.Text(),      nullable=True),
        sa.Column("diet_instructions",         sa.Text(),      nullable=True),
        sa.Column("patient_education_materials", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("discharged_by",             sa.UUID(),      nullable=True),
        sa.Column("discharged_at",             sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["clinic_id"],    ["clinics.id"],    ondelete="CASCADE", name="fk_encounter_dispositions_clinic_id_clinics"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="CASCADE", name="fk_encounter_dispositions_encounter_id_encounters"),
        sa.PrimaryKeyConstraint("id", name="pk_encounter_dispositions"),
        sa.UniqueConstraint("encounter_id", name="uq_encounter_dispositions_encounter_id"),
    )
    op.create_index("ix_encounter_dispositions_clinic_id",    "encounter_dispositions", ["clinic_id"])
    op.create_index("ix_encounter_dispositions_encounter_id", "encounter_dispositions", ["encounter_id"])

    # ── RBAC ──────────────────────────────────────────────────────────

    op.create_table(
        "permissions",
        sa.Column("id",          sa.UUID(), nullable=False),
        sa.Column(
            "action",
            postgresql.ENUM("create","read","update","delete", name="permissionaction", create_type=False),
            nullable=False,
        ),
        sa.Column("resource",    postgresql.ENUM(
            "patient","patient_history","clinical_notes","chief_complaint",
            "vitals","prescription","investigation","nursing_notes",
            "queue","appointment","checkin",
            "user_management","clinic_settings","reports","audit_logs",
            "invoice","payment","fee_template",
            name="permissionresource", create_type=False), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",  sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name="pk_permissions"),
        sa.UniqueConstraint("action","resource", name="uq_permissions_action_resource"),
    )

    op.create_table(
        "role_permissions",
        sa.Column("id",            sa.UUID(),      nullable=False),
        sa.Column("role",          sa.String(50),  nullable=False),
        sa.Column("permission_id", sa.UUID(),      nullable=False),
        sa.Column("created_at",    sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",    sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE", name="fk_role_permissions_permission_id_permissions"),
        sa.PrimaryKeyConstraint("id", name="pk_role_permissions"),
        sa.UniqueConstraint("role","permission_id", name="uq_role_permissions_role_permission"),
    )
    op.create_index("ix_role_permissions_role", "role_permissions", ["role"])

    op.create_table(
        "custom_roles",
        sa.Column("id",            sa.UUID(),      nullable=False),
        sa.Column("clinic_id",     sa.UUID(),      nullable=False),
        sa.Column("name",          sa.String(100), nullable=False),
        sa.Column("slug",          sa.String(100), nullable=False),
        sa.Column("description",   sa.Text(),      nullable=True),
        sa.Column("color",         sa.String(7),   nullable=True),
        sa.Column("based_on_role", sa.String(50),  nullable=True),
        sa.Column("is_active",     sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("created_by",    sa.String(128), nullable=True),
        sa.Column("created_at",    sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",    sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE", name="fk_custom_roles_clinic_id_clinics"),
        sa.PrimaryKeyConstraint("id", name="pk_custom_roles"),
        sa.UniqueConstraint("clinic_id","slug", name="uq_custom_roles_clinic_slug"),
    )
    op.create_index("ix_custom_roles_clinic_id", "custom_roles", ["clinic_id"])

    op.create_table(
        "custom_role_permissions",
        sa.Column("id",             sa.UUID(), nullable=False),
        sa.Column("custom_role_id", sa.UUID(), nullable=False),
        sa.Column(
            "action",
            postgresql.ENUM("create","read","update","delete", name="permissionaction", create_type=False),
            nullable=False,
        ),
        sa.Column("resource", postgresql.ENUM(
            "patient","patient_history","clinical_notes","chief_complaint",
            "vitals","prescription","investigation","nursing_notes",
            "queue","appointment","checkin",
            "user_management","clinic_settings","reports","audit_logs",
            "invoice","payment","fee_template",
            name="permissionresource", create_type=False), nullable=False),
        sa.Column("granted_by", sa.String(128), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["custom_role_id"], ["custom_roles.id"], ondelete="CASCADE", name="fk_custom_role_permissions_custom_role_id_custom_roles"),
        sa.PrimaryKeyConstraint("id", name="pk_custom_role_permissions"),
        sa.UniqueConstraint("custom_role_id","action","resource", name="uq_custom_role_permissions"),
    )

    op.create_table(
        "user_custom_role_assignments",
        sa.Column("id",             sa.UUID(), nullable=False),
        sa.Column("user_id",        sa.UUID(), nullable=False),
        sa.Column("custom_role_id", sa.UUID(), nullable=False),
        sa.Column("clinic_id",      sa.UUID(), nullable=False),
        sa.Column("is_active",      sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("assigned_by",    sa.String(128), nullable=True),
        sa.Column("assigned_at",    sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("revoked_at",     sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"],        ["users.id"],        ondelete="CASCADE", name="fk_user_custom_role_assignments_user_id_users"),
        sa.ForeignKeyConstraint(["custom_role_id"], ["custom_roles.id"], ondelete="CASCADE", name="fk_user_custom_role_assignments_custom_role_id_custom_roles"),
        sa.PrimaryKeyConstraint("id", name="pk_user_custom_role_assignments"),
        sa.UniqueConstraint("user_id","custom_role_id", name="uq_user_custom_role"),
    )
    op.create_index("ix_user_custom_role_assignments_user_id",   "user_custom_role_assignments", ["user_id"])
    op.create_index("ix_user_custom_role_assignments_clinic_id", "user_custom_role_assignments", ["clinic_id"])

    # ── Visit flow ────────────────────────────────────────────────────

    op.create_table(
        "visit_flow_configs",
        sa.Column("id",               sa.UUID(),      nullable=False),
        sa.Column("clinic_id",        sa.UUID(),      nullable=False),
        sa.Column("flow_name",        sa.String(100), nullable=False, server_default="Standard OPD Flow"),
        sa.Column("billing_required", sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("direct_to_doctor", sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("auto_assign_nurse",sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("last_modified_by", sa.String(128), nullable=True),
        sa.Column("created_at",       sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",       sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE", name="fk_visit_flow_configs_clinic_id_clinics"),
        sa.PrimaryKeyConstraint("id", name="pk_visit_flow_configs"),
        sa.UniqueConstraint("clinic_id", name="uq_visit_flow_configs_clinic_id"),
    )
    op.create_index("ix_visit_flow_configs_clinic_id", "visit_flow_configs", ["clinic_id"])

    op.create_table(
        "visit_state_configs",
        sa.Column("id",             sa.UUID(),      nullable=False),
        sa.Column("flow_config_id", sa.UUID(),      nullable=False),
        sa.Column("state",          sa.String(60),  nullable=False),
        sa.Column("is_active",      sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("is_mandatory",   sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("display_label",  sa.String(100), nullable=True),
        sa.Column("description",    sa.Text(),      nullable=True),
        sa.Column("order_index",    sa.Integer(),   nullable=False),
        sa.Column("sla_minutes",    sa.Integer(),   nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["flow_config_id"], ["visit_flow_configs.id"], ondelete="CASCADE", name="fk_visit_state_configs_flow_config_id_visit_flow_configs"),
        sa.PrimaryKeyConstraint("id", name="pk_visit_state_configs"),
        sa.UniqueConstraint("flow_config_id","state", name="uq_visit_state_configs_flow_state"),
    )

    op.create_table(
        "visit_transition_rules",
        sa.Column("id",             sa.UUID(),      nullable=False),
        sa.Column("flow_config_id", sa.UUID(),      nullable=False),
        sa.Column("from_state",     sa.String(60),  nullable=False),
        sa.Column("to_state",       sa.String(60),  nullable=False),
        sa.Column("is_active",      sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("allowed_roles",  postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("is_bypass",      sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("requires_note",  sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("created_by",     sa.String(128), nullable=True),
        sa.Column("updated_at",     sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["flow_config_id"], ["visit_flow_configs.id"], ondelete="CASCADE", name="fk_visit_transition_rules_flow_config_id_visit_flow_configs"),
        sa.PrimaryKeyConstraint("id", name="pk_visit_transition_rules"),
        sa.UniqueConstraint("flow_config_id","from_state","to_state", name="uq_visit_transition_rules"),
    )


def downgrade() -> None:
    tables = [
        "visit_transition_rules", "visit_state_configs", "visit_flow_configs",
        "user_custom_role_assignments", "custom_role_permissions", "custom_roles",
        "role_permissions", "permissions",
        "encounter_dispositions", "encounter_medications", "encounter_orders",
        "encounter_diagnoses", "encounter_notes", "encounter_vitals", "encounters",
        "patient_backgrounds", "patients", "users", "clinics",
    ]
    for t in tables:
        op.drop_table(t)
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS permissionaction")
    op.execute("DROP TYPE IF EXISTS permissionresource")
