"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import { useApiClient } from "@/lib/axios";
import type {
  Encounter,
  EncounterListResponse,
  EncounterStatus,
  QueueFilters,
  TriageAssessment,
  TodaySummary,
} from "@/types/encounter-queue";

const POLL_INTERVAL = 15_000; // 15 s auto-refresh

function isNetworkChangedError(error: unknown): boolean {
  const maybeAxios = error as AxiosError | undefined;
  const msg = String(maybeAxios?.message ?? "").toUpperCase();
  // Browser-level transient during adapter/VPN switching.
  return msg.includes("ERR_NETWORK_CHANGED") || msg.includes("NETWORK_CHANGED");
}

// ── Queue list ──

export function useEncounterQueue(filters: QueueFilters) {
  const { api, isReady } = useApiClient();

  return useQuery<EncounterListResponse>({
    queryKey: ["encounter-queue", filters],
    queryFn: async () => {
      const params: Record<string, string | number> = { page: 1, size: 100 };
      if (filters.status) params.status = filters.status;
      if (filters.encounter_type) params.encounter_type = filters.encounter_type;
      if (filters.provider_id) params.provider_id = filters.provider_id;
      if (filters.department_id) params.department_id = filters.department_id;
      if (filters.search) params.search = filters.search;

      const { data } = await api.get<EncounterListResponse>("/encounters/queue", { params });
      return data;
    },
    enabled: isReady,
    retry: (failureCount, error) => {
      if (isNetworkChangedError(error)) return failureCount < 6;
      return failureCount < 2;
    },
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10_000),
    refetchInterval: POLL_INTERVAL,
    staleTime: 5_000,
  });
}

// ── Today summary ──

export function useTodaySummary() {
  const { api, isReady } = useApiClient();

  return useQuery<TodaySummary>({
    queryKey: ["encounter-today-summary"],
    queryFn: async () => {
      const { data } = await api.get<TodaySummary>("/encounters/today");
      return data;
    },
    enabled: isReady,
    retry: (failureCount, error) => {
      if (isNetworkChangedError(error)) return failureCount < 6;
      return failureCount < 2;
    },
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10_000),
    refetchInterval: POLL_INTERVAL,
    staleTime: 5_000,
  });
}

// ── Status mutation (optimistic) ──

export function useUpdateEncounterStatus() {
  const { api } = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      status,
      triageAssessment,
    }: {
      id: string;
      status: EncounterStatus;
      triageAssessment?: TriageAssessment;
    }) => {
      const payload: {
        status: EncounterStatus;
        triage_assessment?: TriageAssessment;
      } = { status };
      if (triageAssessment) {
        payload.triage_assessment = triageAssessment;
      }
      const { data } = await api.patch<Encounter>(`/encounters/${id}/status`, payload);
      return data;
    },
    onMutate: async ({ id, status, triageAssessment }) => {
      await queryClient.cancelQueries({ queryKey: ["encounter-queue"] });
      const previous = queryClient.getQueriesData<EncounterListResponse>({
        queryKey: ["encounter-queue"],
      });
      queryClient.setQueriesData<EncounterListResponse>(
        { queryKey: ["encounter-queue"] },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            items: old.items.map((enc) =>
              enc.id === id
                ? {
                    ...enc,
                    status,
                    triage_assessment: triageAssessment ?? enc.triage_assessment,
                  }
                : enc
            ),
          };
        }
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      context?.previous?.forEach(([key, data]) => {
        if (data) queryClient.setQueryData(key, data);
      });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["encounter-queue"] });
      queryClient.invalidateQueries({ queryKey: ["encounter-today-summary"] });
    },
  });
}

// ── Encounter detail ──

export function useEncounterDetail(id: string | null) {
  const { api, isReady } = useApiClient();

  return useQuery<Encounter>({
    queryKey: ["encounter-detail", id],
    queryFn: async () => {
      const { data } = await api.get<Encounter>(`/encounters/${id}`);
      return data;
    },
    enabled: isReady && Boolean(id),
  });
}

// ── Elapsed timer hook ──

export function useElapsed(since: string | null): string {
  const [now, setNow] = useState(Date.now);

  useEffect(() => {
    if (!since) return;
    const id = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(id);
  }, [since]);

  if (!since) return "-";
  const diffMs = now - new Date(since).getTime();
  if (diffMs < 0) return "0m";
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ${mins % 60}m`;
}

// ── CSV export ──

export function useExportQueueCsv() {
  const exportCsv = useCallback((encounters: Encounter[]) => {
    const header = [
      "Encounter ID",
      "Patient",
      "Type",
      "Status",
      "Chief Complaint",
      "Provider ID",
      "Checked-In At",
      "Created At",
    ].join(",");

    const rows = encounters.map((e) => {
      const name = e.patient
        ? `${e.patient.first_name} ${e.patient.last_name}`
        : e.patient_id;
      return [
        e.encounter_id,
        `"${name}"`,
        e.encounter_type,
        e.status,
        `"${(e.chief_complaint ?? "").replace(/"/g, '""')}"`,
        e.provider_id ?? "",
        e.checked_in_at ?? "",
        e.created_at,
      ].join(",");
    });

    const csv = [header, ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `encounter-queue-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  return exportCsv;
}
