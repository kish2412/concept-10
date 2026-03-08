/**
 * Shared test fixture factory for React component tests.
 * Produces fully-typed Encounter objects matching the TS types
 * without requiring network or backend.
 */

import type {
  Encounter,
  DispositionRecord,
  MedicationRecord,
  NoteRecord,
  OrderRecord,
  VitalsRecord,
} from "@/types/encounter-queue";

const CLINIC_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const PATIENT_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";
const PROVIDER_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc";

let _counter = 0;
function uid(): string {
  _counter += 1;
  return `00000000-0000-0000-0000-${String(_counter).padStart(12, "0")}`;
}

export function buildEncounter(overrides: Partial<Encounter> = {}): Encounter {
  return {
    id: uid(),
    clinic_id: CLINIC_ID,
    encounter_id: `ENC-20260307-${String(_counter).padStart(4, "0")}`,
    patient_id: PATIENT_ID,
    provider_id: PROVIDER_ID,
    facility_id: null,
    department_id: null,
    encounter_type: "CONSULTATION",
    status: "CHECKED_IN",
    chief_complaint: "Chest pain",
    scheduled_at: null,
    checked_in_at: new Date(Date.now() - 15 * 60_000).toISOString(), // 15 min ago
    triage_at: null,
    started_at: null,
    ended_at: null,
    created_by: PROVIDER_ID,
    updated_by: null,
    deleted_at: null,
    created_at: new Date(Date.now() - 20 * 60_000).toISOString(),
    updated_at: new Date().toISOString(),
    is_deleted: false,
    patient: { id: PATIENT_ID, first_name: "Jane", last_name: "Doe" },
    vitals: [],
    notes: [],
    diagnoses: [],
    orders: [],
    medications: [],
    disposition: null,
    ...overrides,
  };
}

export function buildVitals(overrides: Partial<VitalsRecord> = {}): VitalsRecord {
  return {
    id: uid(),
    blood_pressure_systolic: 120,
    blood_pressure_diastolic: 80,
    pulse_rate: 72,
    respiratory_rate: 16,
    temperature: 37.0,
    oxygen_saturation: 98,
    weight: 70,
    height: 170,
    bmi: 24.22,
    pain_score: 3,
    recorded_by: PROVIDER_ID,
    recorded_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

export function buildNote(overrides: Partial<NoteRecord> = {}): NoteRecord {
  return {
    id: uid(),
    note_type: "SOAP",
    subjective: "Patient reports chest pain",
    objective: "BP 140/90, HR 88",
    assessment: "Possible angina",
    plan: "Order troponin, ECG",
    author_id: PROVIDER_ID,
    author_role: "provider",
    is_signed: false,
    signed_at: null,
    version: 1,
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

export function buildOrder(overrides: Partial<OrderRecord> = {}): OrderRecord {
  return {
    id: uid(),
    order_type: "LAB",
    order_code: null,
    order_description: "CBC with differential",
    status: "PENDING",
    priority: "ROUTINE",
    ordered_by: PROVIDER_ID,
    ordered_at: new Date().toISOString(),
    result_summary: null,
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

export function buildMedication(
  overrides: Partial<MedicationRecord> = {},
): MedicationRecord {
  return {
    id: uid(),
    drug_code: null,
    drug_name: "Aspirin",
    generic_name: "Acetylsalicylic acid",
    dosage: "81",
    dosage_unit: "mg",
    frequency: "QD",
    route: "PO",
    duration_days: 30,
    quantity: 30,
    special_instructions: null,
    is_controlled_substance: false,
    prescribed_by: PROVIDER_ID,
    prescribed_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

export function buildDisposition(
  overrides: Partial<DispositionRecord> = {},
): DispositionRecord {
  return {
    id: uid(),
    disposition_type: "DISCHARGE",
    follow_up_required: true,
    follow_up_in_days: 7,
    discharge_instructions: "Rest, follow up in 1 week",
    activity_restrictions: "No heavy lifting",
    diet_instructions: "Low sodium",
    discharged_by: PROVIDER_ID,
    discharged_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    ...overrides,
  };
}
