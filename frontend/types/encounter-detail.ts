// Types for the Encounter Detail page

export type PatientDetail = {
  id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string | null;
  // Backend currently does not expose MRN; UI derives a display MRN fallback.
  mrn: string | null;
  allergies: string[];
  chronic_conditions: string[];
  current_medications: string[];
};

export type PatientBackgroundDetail = {
  id: string;
  patient_id: string;
  current_medications: string | null;
  medical_history: string | null;
  surgical_history: string | null;
  family_history: string | null;
  social_history: string | null;
};

export type EncounterEvent = {
  id: string;
  event_type: string;
  description: string;
  user_id: string | null;
  timestamp: string;
};

export type NoteVersion = {
  version: number;
  subjective: string | null;
  objective: string | null;
  assessment: string | null;
  plan: string | null;
  created_at: string;
  author_id: string | null;
};

export type ICD10SearchResult = {
  code: string;
  description: string;
};

export type DrugSearchResult = {
  code: string;
  name: string;
  generic_name: string;
  interactions: string[];
  is_controlled: boolean;
};

export type PatientEducationMaterial = {
  id: string;
  title: string;
  url: string;
};

export type TriageAISummary = {
  encounter_id: string;
  summary: string;
  clinician_focus_points: string[];
  red_flags: string[];
  missing_information: string[];
  generated_at: string;
  orchestration: string;
  model_provider: string;
  model_name: string;
  guardrail_profile: string | null;
};

// Order form field types based on order type
export const ORDER_TYPES = ["LAB", "IMAGING", "MEDICATION", "REFERRAL"] as const;
export type OrderType = (typeof ORDER_TYPES)[number];

export const ORDER_TYPE_LABELS: Record<OrderType, string> = {
  LAB: "Lab",
  IMAGING: "Imaging",
  MEDICATION: "Medication",
  REFERRAL: "Referral",
};

export const ORDER_STATUSES = ["PENDING", "SENT", "IN_PROGRESS", "RESULTED"] as const;
export type OrderStatusType = (typeof ORDER_STATUSES)[number];

export const ORDER_PRIORITIES = ["ROUTINE", "URGENT", "STAT"] as const;
export type OrderPriorityType = (typeof ORDER_PRIORITIES)[number];

export const DISPOSITION_TYPES = [
  "DISCHARGE",
  "ADMIT",
  "REFER_ER",
  "REFER_SPECIALIST",
] as const;
export type DispositionType = (typeof DISPOSITION_TYPES)[number];

export const DISPOSITION_LABELS: Record<string, string> = {
  DISCHARGE: "Discharge",
  ADMIT: "Admit",
  REFER_ER: "Refer to ER",
  REFER_SPECIALIST: "Refer to Specialist",
};

export const DIAGNOSIS_TYPES = [
  "PRIMARY",
  "SECONDARY",
  "DIFFERENTIAL",
  "RULE_OUT",
] as const;
export type DiagnosisTypeValue = (typeof DIAGNOSIS_TYPES)[number];

export const MEDICATION_ROUTES = [
  "Oral",
  "IV",
  "IM",
  "Subcutaneous",
  "Topical",
  "Inhaled",
  "Rectal",
  "Sublingual",
  "Transdermal",
] as const;

export const MEDICATION_FREQUENCIES = [
  "Once daily",
  "Twice daily",
  "Three times daily",
  "Four times daily",
  "Every 4 hours",
  "Every 6 hours",
  "Every 8 hours",
  "Every 12 hours",
  "As needed (PRN)",
  "At bedtime",
  "Before meals",
  "After meals",
] as const;
