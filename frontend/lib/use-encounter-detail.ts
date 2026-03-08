"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "@/lib/axios";
import type { Encounter } from "@/types/encounter-queue";
import type {
  DrugSearchResult,
  ICD10SearchResult,
  PatientBackgroundDetail,
  PatientDetail,
  TriageAISummary,
} from "@/types/encounter-detail";
import type {
  DiagnosisRecord,
  DispositionRecord,
  MedicationRecord,
  NoteRecord,
  OrderRecord,
  VitalsRecord,
} from "@/types/encounter-queue";

// ── Full encounter detail with polling ──

export function useEncounterDetailPage(id: string) {
  const { api, isReady } = useApiClient();

  return useQuery<Encounter>({
    queryKey: ["encounter-detail", id],
    queryFn: async () => {
      const { data } = await api.get<Encounter>(`/encounters/${id}`);
      return data;
    },
    enabled: isReady && Boolean(id),
    refetchInterval: 30_000,
  });
}

// ── Patient encounters history (for copy-forward) ──

export function usePatientEncounters(patientId: string | null) {
  const { api, isReady } = useApiClient();

  return useQuery<{ items: Encounter[] }>({
    queryKey: ["patient-encounters", patientId],
    queryFn: async () => {
      const { data } = await api.get(`/encounters/patient/${patientId}`, {
        params: { page: 1, size: 10 },
      });
      return data;
    },
    enabled: isReady && Boolean(patientId),
  });
}

export function usePatientProfile(patientId: string | null) {
  const { api, isReady } = useApiClient();

  return useQuery<{ patient: PatientDetail; background: PatientBackgroundDetail | null }>({
    queryKey: ["patient-profile", patientId],
    queryFn: async () => {
      const [{ data: patient }, { data: background }] = await Promise.all([
        api.get<PatientDetail>(`/patients/${patientId}`),
        api.get<PatientBackgroundDetail>(`/patients/${patientId}/background`),
      ]);

      return { patient, background: background ?? null };
    },
    enabled: isReady && Boolean(patientId),
    staleTime: 60_000,
  });
}

// ── Notes CRUD ──

export function useAddNote(encounterId: string) {
  const { api } = useApiClient();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (note: {
      note_type: string;
      subjective: string;
      objective: string;
      assessment: string;
      plan: string;
    }) => {
      const { data } = await api.post<NoteRecord>(
        `/encounters/${encounterId}/notes`,
        note
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["encounter-detail", encounterId] });
    },
  });
}

export function useUpdateNote(encounterId: string) {
  const { api } = useApiClient();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async ({
      noteId,
      ...body
    }: {
      noteId: string;
      subjective: string;
      objective: string;
      assessment: string;
      plan: string;
    }) => {
      const { data } = await api.put<NoteRecord>(
        `/encounters/${encounterId}/notes/${noteId}`,
        body
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["encounter-detail", encounterId] });
    },
  });
}

export function useSignNote(encounterId: string) {
  const { api } = useApiClient();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (noteId: string) => {
      const { data } = await api.post<NoteRecord>(
        `/encounters/${encounterId}/notes/${noteId}/sign`
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["encounter-detail", encounterId] });
    },
  });
}

// ── Diagnoses CRUD ──

export function useAddDiagnosis(encounterId: string) {
  const { api } = useApiClient();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (dx: {
      icd_code: string;
      icd_description: string;
      diagnosis_type: string;
      is_chronic_condition: boolean;
    }) => {
      const { data } = await api.post<DiagnosisRecord>(
        `/encounters/${encounterId}/diagnoses`,
        dx
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["encounter-detail", encounterId] });
    },
  });
}

export function useRemoveDiagnosis(encounterId: string) {
  const { api } = useApiClient();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (diagnosisId: string) => {
      await api.delete(`/encounters/${encounterId}/diagnoses/${diagnosisId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["encounter-detail", encounterId] });
    },
  });
}

// ── ICD-10 search ──

export function useICD10Search(query: string) {
  const { api, isReady } = useApiClient();

  return useQuery<ICD10SearchResult[]>({
    queryKey: ["icd10-search", query],
    queryFn: async () => {
      const { data } = await api.get<ICD10SearchResult[]>("/lookup/icd10", {
        params: { q: query },
      });
      return data;
    },
    enabled: isReady && query.length >= 2,
    staleTime: 60_000,
  });
}

// ── Orders CRUD ──

export function useAddOrder(encounterId: string) {
  const { api } = useApiClient();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (order: {
      order_type: string;
      order_code?: string;
      order_description: string;
      priority: string;
    }) => {
      const { data } = await api.post<OrderRecord>(
        `/encounters/${encounterId}/orders`,
        order
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["encounter-detail", encounterId] });
    },
  });
}

export function useUpdateOrderStatus(encounterId: string) {
  const { api } = useApiClient();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async ({
      orderId,
      status,
    }: {
      orderId: string;
      status: string;
    }) => {
      const { data } = await api.patch<OrderRecord>(
        `/encounters/${encounterId}/orders/${orderId}`,
        { status }
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["encounter-detail", encounterId] });
    },
  });
}

// ── Medications CRUD ──

export function useAddMedication(encounterId: string) {
  const { api } = useApiClient();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (med: {
      drug_name: string;
      generic_name?: string;
      drug_code?: string;
      dosage: string;
      dosage_unit: string;
      frequency: string;
      route: string;
      duration_days?: number;
      quantity?: number;
      special_instructions?: string;
      is_controlled_substance: boolean;
    }) => {
      const { data } = await api.post<MedicationRecord>(
        `/encounters/${encounterId}/medications`,
        med
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["encounter-detail", encounterId] });
    },
  });
}

export function useRemoveMedication(encounterId: string) {
  const { api } = useApiClient();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (medId: string) => {
      await api.delete(`/encounters/${encounterId}/medications/${medId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["encounter-detail", encounterId] });
    },
  });
}

// ── Drug search ──

export function useDrugSearch(query: string) {
  const { api, isReady } = useApiClient();

  return useQuery<DrugSearchResult[]>({
    queryKey: ["drug-search", query],
    queryFn: async () => {
      const { data } = await api.get<DrugSearchResult[]>("/lookup/drugs", {
        params: { q: query },
      });
      return data;
    },
    enabled: isReady && query.length >= 2,
    staleTime: 60_000,
  });
}

// ── Disposition ──

export function useSaveDisposition(encounterId: string) {
  const { api } = useApiClient();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (dispo: {
      disposition_id?: string;
      disposition_type: string;
      follow_up_required: boolean;
      follow_up_in_days?: number;
      discharge_instructions?: string;
      activity_restrictions?: string;
      diet_instructions?: string;
      patient_education_materials?: string[];
    }) => {
      const { disposition_id, ...payload } = dispo;
      const { data } = disposition_id
        ? await api.put<DispositionRecord>(
            `/encounters/${encounterId}/disposition/${disposition_id}`,
            payload
          )
        : await api.post<DispositionRecord>(
            `/encounters/${encounterId}/disposition`,
            payload
          );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["encounter-detail", encounterId] });
    },
  });
}

// ── Complete encounter (discharge) ──

export function useCompleteEncounter(encounterId: string) {
  const { api } = useApiClient();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const { data } = await api.patch<Encounter>(
        `/encounters/${encounterId}/status`,
        { status: "DISCHARGED" }
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["encounter-detail", encounterId] });
      qc.invalidateQueries({ queryKey: ["encounter-queue"] });
    },
  });
}

// ── Vitals ──

export function useAddVitals(encounterId: string) {
  const { api } = useApiClient();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (vitals: {
      blood_pressure_systolic?: number;
      blood_pressure_diastolic?: number;
      pulse_rate?: number;
      respiratory_rate?: number;
      temperature?: number;
      oxygen_saturation?: number;
      weight?: number;
      height?: number;
      pain_score?: number;
    }) => {
      const { data } = await api.post<VitalsRecord>(
        `/encounters/${encounterId}/vitals`,
        vitals
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["encounter-detail", encounterId] });
    },
  });
}

// ── AI triage summary ──

export function useGenerateTriageSummary(encounterId: string) {
  const { api } = useApiClient();

  return useMutation({
    mutationFn: async (regenerate: boolean = false) => {
      const { data } = await api.post<TriageAISummary>(
        `/encounters/${encounterId}/ai/triage-summary`,
        { regenerate }
      );
      return data;
    },
  });
}

// ── Auto-save hook ──

export function useAutoSave(
  saveFn: () => void | Promise<unknown>,
  intervalMs: number = 30_000,
  enabled: boolean = true
) {
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const saveFnRef = useRef(saveFn);
  saveFnRef.current = saveFn;

  useEffect(() => {
    if (!enabled) return;
    const id = setInterval(() => {
      Promise.resolve(saveFnRef.current())
        .then(() => setLastSaved(new Date()))
        .catch(() => {
          // Keep lastSaved unchanged if autosave fails.
        });
    }, intervalMs);
    return () => clearInterval(id);
  }, [intervalMs, enabled]);

  return { lastSaved };
}

// ── Unsaved changes detection ──

export function useUnsavedChanges(hasChanges: boolean) {
  useEffect(() => {
    if (!hasChanges) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [hasChanges]);
}

// ── Debounced value ──

export function useDebouncedValue<T>(value: T, delayMs: number = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(id);
  }, [value, delayMs]);

  return debounced;
}
