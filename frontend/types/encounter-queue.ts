// Shared types for Encounter Queue Dashboard

export type PatientSummary = {
  id: string;
  first_name: string;
  last_name: string;
};

export type Encounter = {
  id: string;
  clinic_id: string;
  encounter_id: string;
  patient_id: string;
  provider_id: string | null;
  facility_id: string | null;
  department_id: string | null;
  encounter_type: EncounterType;
  status: EncounterStatus;
  chief_complaint: string | null;
  scheduled_at: string | null;
  checked_in_at: string | null;
  triage_at: string | null;
  started_at: string | null;
  ended_at: string | null;
  created_by: string | null;
  updated_by: string | null;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
  patient: PatientSummary | null;
  vitals: VitalsRecord[];
  notes: NoteRecord[];
  diagnoses: DiagnosisRecord[];
  orders: OrderRecord[];
  medications: MedicationRecord[];
  disposition: DispositionRecord | null;
};

export type VitalsRecord = {
  id: string;
  blood_pressure_systolic: number | null;
  blood_pressure_diastolic: number | null;
  pulse_rate: number | null;
  respiratory_rate: number | null;
  temperature: number | null;
  oxygen_saturation: number | null;
  weight: number | null;
  height: number | null;
  bmi: number | null;
  pain_score: number | null;
  recorded_by: string | null;
  recorded_at: string | null;
  created_at: string;
};

export type NoteRecord = {
  id: string;
  note_type: string;
  subjective: string | null;
  objective: string | null;
  assessment: string | null;
  plan: string | null;
  author_id: string | null;
  author_role: string | null;
  is_signed: boolean;
  signed_at: string | null;
  version: number;
  created_at: string;
};

export type DiagnosisRecord = {
  id: string;
  icd_code: string;
  icd_description: string;
  diagnosis_type: string;
  onset_date: string | null;
  is_chronic_condition: boolean;
  added_by: string | null;
  created_at: string;
};

export type OrderRecord = {
  id: string;
  order_type: string;
  order_code: string | null;
  order_description: string;
  status: string;
  priority: string;
  ordered_by: string | null;
  ordered_at: string | null;
  result_summary: string | null;
  created_at: string;
};

export type MedicationRecord = {
  id: string;
  drug_code: string | null;
  drug_name: string;
  generic_name: string | null;
  dosage: string;
  dosage_unit: string;
  frequency: string;
  route: string;
  duration_days: number | null;
  quantity: number | null;
  special_instructions: string | null;
  is_controlled_substance: boolean;
  prescribed_by: string | null;
  prescribed_at: string | null;
  created_at: string;
};

export type DispositionRecord = {
  id: string;
  disposition_type: string;
  follow_up_required: boolean;
  follow_up_in_days: number | null;
  discharge_instructions: string | null;
  activity_restrictions: string | null;
  diet_instructions: string | null;
  patient_education_materials?: string[] | Record<string, unknown> | null;
  discharged_by: string | null;
  discharged_at: string | null;
  created_at: string;
};

export type EncounterListResponse = {
  items: Encounter[];
  total: number;
  page: number;
  size: number;
};

export type TodaySummary = {
  total: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
};

// ── Constants ──

export const ENCOUNTER_TYPES = [
  "CONSULTATION",
  "FOLLOW_UP",
  "EMERGENCY",
  "PROCEDURE",
  "TELECONSULT",
] as const;
export type EncounterType = (typeof ENCOUNTER_TYPES)[number];

export const ENCOUNTER_STATUSES = [
  "SCHEDULED",
  "CHECKED_IN",
  "TRIAGE",
  "WITH_PROVIDER",
  "PENDING_RESULTS",
  "PENDING_REVIEW",
  "DISCHARGED",
  "CANCELLED",
  "NO_SHOW",
] as const;
export type EncounterStatus = (typeof ENCOUNTER_STATUSES)[number];

/** Statuses shown as kanban columns (active workflow stages). */
export const QUEUE_STATUSES: EncounterStatus[] = [
  "CHECKED_IN",
  "TRIAGE",
  "WITH_PROVIDER",
  "PENDING_RESULTS",
  "PENDING_REVIEW",
];

export const STATUS_COLOR: Record<string, string> = {
  SCHEDULED: "bg-slate-100 text-slate-700 border-slate-300",
  CHECKED_IN: "bg-blue-100 text-blue-800 border-blue-300",
  TRIAGE: "bg-yellow-100 text-yellow-800 border-yellow-300",
  WITH_PROVIDER: "bg-green-100 text-green-800 border-green-300",
  PENDING_RESULTS: "bg-orange-100 text-orange-800 border-orange-300",
  PENDING_REVIEW: "bg-purple-100 text-purple-800 border-purple-300",
  DISCHARGED: "bg-gray-100 text-gray-600 border-gray-300",
  CANCELLED: "bg-red-100 text-red-700 border-red-300",
  NO_SHOW: "bg-red-50 text-red-600 border-red-200",
};

export const STATUS_LABEL: Record<string, string> = {
  SCHEDULED: "Scheduled",
  CHECKED_IN: "Checked In",
  TRIAGE: "Triage",
  WITH_PROVIDER: "In Consultation",
  PENDING_RESULTS: "Pending Results",
  PENDING_REVIEW: "Pending Review",
  DISCHARGED: "Discharged",
  CANCELLED: "Cancelled",
  NO_SHOW: "No Show",
};

export const TYPE_LABEL: Record<string, string> = {
  CONSULTATION: "Consultation",
  FOLLOW_UP: "Follow-up",
  EMERGENCY: "Emergency",
  PROCEDURE: "Procedure",
  TELECONSULT: "Teleconsult",
};

/** Next status in the standard workflow. */
export const NEXT_STATUS: Partial<Record<EncounterStatus, EncounterStatus>> = {
  CHECKED_IN: "TRIAGE",
  TRIAGE: "WITH_PROVIDER",
  WITH_PROVIDER: "PENDING_RESULTS",
  PENDING_RESULTS: "PENDING_REVIEW",
  PENDING_REVIEW: "DISCHARGED",
};

export type QueueFilters = {
  search: string;
  status: string;
  encounter_type: string;
  provider_id: string;
  department_id: string;
};
