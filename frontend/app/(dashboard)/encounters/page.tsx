"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";

import { useApiClient } from "@/lib/axios";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";

// ────────────────────────────── Types ──────────────────────────────

type PatientSummary = {
  id: string;
  first_name: string;
  last_name: string;
};

type Encounter = {
  id: string;
  clinic_id: string;
  encounter_id: string;
  patient_id: string;
  provider_id: string | null;
  facility_id: string | null;
  department_id: string | null;
  encounter_type: string;
  status: string;
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
};

type EncounterListResponse = {
  items: Encounter[];
  total: number;
  page: number;
  size: number;
};

type Patient = {
  id: string;
  first_name: string;
  last_name: string;
};

type PatientsListResponse = {
  items: Patient[];
  total: number;
  page: number;
  size: number;
};

// ────────────────────────────── Schema ──────────────────────────────

const ENCOUNTER_TYPES = [
  "CONSULTATION",
  "FOLLOW_UP",
  "EMERGENCY",
  "PROCEDURE",
  "TELECONSULT",
] as const;

const ENCOUNTER_STATUSES = [
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

const encounterFormSchema = z.object({
  patient_id: z.string().min(1, "Patient is required"),
  encounter_type: z.enum(ENCOUNTER_TYPES),
  status: z.enum(ENCOUNTER_STATUSES),
  scheduled_at: z.string().optional(),
  chief_complaint: z.string().optional(),
});

type EncounterFormValues = z.infer<typeof encounterFormSchema>;

const defaultFormValues: EncounterFormValues = {
  patient_id: "",
  encounter_type: "CONSULTATION",
  status: "SCHEDULED",
  scheduled_at: "",
  chief_complaint: "",
};

// ────────────────────────────── Helpers ──────────────────────────────

const ENCOUNTER_TYPE_LABELS: Record<string, string> = {
  CONSULTATION: "Consultation",
  FOLLOW_UP: "Follow-up",
  EMERGENCY: "Emergency",
  PROCEDURE: "Procedure",
  TELECONSULT: "Teleconsult",
};

const STATUS_VARIANT: Record<string, "default" | "secondary"> = {
  SCHEDULED: "secondary",
  CHECKED_IN: "default",
  TRIAGE: "default",
  WITH_PROVIDER: "default",
  PENDING_RESULTS: "secondary",
  PENDING_REVIEW: "secondary",
  DISCHARGED: "secondary",
  CANCELLED: "secondary",
  NO_SHOW: "secondary",
};

const STATUS_LABELS: Record<string, string> = {
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

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ────────────────────────────── Page ──────────────────────────────

export default function EncountersPage() {
  const router = useRouter();
  const { api, isReady } = useApiClient();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [editingEncounter, setEditingEncounter] = useState<Encounter | null>(
    null
  );

  const form = useForm<EncounterFormValues>({
    resolver: zodResolver(encounterFormSchema),
    defaultValues: defaultFormValues,
  });

  // ── Fetch encounters ──
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["encounters", search, statusFilter],
    queryFn: async () => {
      const params: Record<string, string | number> = { page: 1, size: 50 };
      if (search) params.search = search;
      if (statusFilter) params.status = statusFilter;
      const response = await api.get<EncounterListResponse>("/encounters", {
        params,
      });
      return response.data;
    },
    enabled: isReady,
  });

  // ── Fetch patients for the dropdown ──
  const { data: patientsData } = useQuery({
    queryKey: ["patients-lookup"],
    queryFn: async () => {
      const response = await api.get<PatientsListResponse>("/patients", {
        params: { page: 1, size: 100 },
      });
      return response.data;
    },
    enabled: isReady,
  });

  const patients = useMemo(
    () => patientsData?.items ?? [],
    [patientsData?.items]
  );

  // ── Mutations ──
  const createMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      await api.post("/encounters", payload);
    },
    onSuccess: async () => {
      setIsDrawerOpen(false);
      setEditingEncounter(null);
      form.reset(defaultFormValues);
      await queryClient.invalidateQueries({ queryKey: ["encounters"] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: string;
      payload: Record<string, unknown>;
    }) => {
      await api.put(`/encounters/${id}`, payload);
    },
    onSuccess: async () => {
      setIsDrawerOpen(false);
      setEditingEncounter(null);
      form.reset(defaultFormValues);
      await queryClient.invalidateQueries({ queryKey: ["encounters"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/encounters/${id}`);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["encounters"] });
    },
  });

  const encounters = useMemo(() => data?.items ?? [], [data?.items]);
  const isSubmitting = createMutation.isPending || updateMutation.isPending;
  const submitError = createMutation.isError || updateMutation.isError;
  const isEditMode = Boolean(editingEncounter);

  // ── Form helpers ──

  function resetFormState(open: boolean) {
    setIsDrawerOpen(open);
    if (!open) {
      setEditingEncounter(null);
      form.reset(defaultFormValues);
    }
  }

  function toPayload(values: EncounterFormValues) {
    return {
      patient_id: values.patient_id,
      encounter_type: values.encounter_type,
      status: values.status,
      scheduled_at: values.scheduled_at || null,
      chief_complaint: values.chief_complaint?.trim() || null,
    };
  }

  function openAddDrawer() {
    setEditingEncounter(null);
    form.reset(defaultFormValues);
    setIsDrawerOpen(true);
  }

  function openEditDrawer(enc: Encounter) {
    setEditingEncounter(enc);
    form.reset({
      patient_id: enc.patient_id,
      encounter_type: enc.encounter_type as EncounterFormValues["encounter_type"],
      status: enc.status as EncounterFormValues["status"],
      scheduled_at: enc.scheduled_at
        ? new Date(enc.scheduled_at).toISOString().slice(0, 16)
        : "",
      chief_complaint: enc.chief_complaint ?? "",
    });
    setIsDrawerOpen(true);
  }

  function onSubmit(values: EncounterFormValues) {
    const payload = toPayload(values);
    if (editingEncounter) {
      updateMutation.mutate({ id: editingEncounter.id, payload });
      return;
    }
    createMutation.mutate(payload);
  }

  function getPatientName(enc: Encounter): string {
    if (enc.patient) {
      return `${enc.patient.first_name} ${enc.patient.last_name}`;
    }
    const p = patients.find((pt) => pt.id === enc.patient_id);
    return p ? `${p.first_name} ${p.last_name}` : enc.patient_id;
  }

  // ────────────────────────────── Render ──────────────────────────────

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Encounters</h1>

        <Sheet open={isDrawerOpen} onOpenChange={resetFormState}>
          <SheetTrigger asChild>
            <Button onClick={openAddDrawer}>New Encounter</Button>
          </SheetTrigger>
          <SheetContent className="overflow-y-auto sm:max-w-lg">
            <SheetHeader>
              <SheetTitle>
                {isEditMode ? "Edit Encounter" : "New Encounter"}
              </SheetTitle>
              <SheetDescription>
                {isEditMode
                  ? "Update encounter details."
                  : "Record a new patient encounter."}
              </SheetDescription>
              {isEditMode && editingEncounter ? (
                <div className="pt-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setIsDrawerOpen(false);
                      router.push(`/encounters/${editingEncounter.id}`);
                    }}
                  >
                    Open Full Encounter Workspace
                  </Button>
                </div>
              ) : null}
            </SheetHeader>

            <Form {...form}>
              <form
                className="mt-6 space-y-4"
                onSubmit={form.handleSubmit(onSubmit)}
              >
                {/* Patient select */}
                <FormField
                  control={form.control}
                  name="patient_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>
                        Patient <span className="text-red-500">*</span>
                      </FormLabel>
                      <FormControl>
                        <select
                          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                          value={field.value}
                          onChange={field.onChange}
                        >
                          <option value="">Select patient…</option>
                          {patients.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.first_name} {p.last_name}
                            </option>
                          ))}
                        </select>
                      </FormControl>
                      <FormMessage name={field.name} />
                    </FormItem>
                  )}
                />

                {/* Encounter type */}
                <FormField
                  control={form.control}
                  name="encounter_type"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Type</FormLabel>
                      <FormControl>
                        <select
                          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                          value={field.value}
                          onChange={field.onChange}
                        >
                          {ENCOUNTER_TYPES.map((t) => (
                            <option key={t} value={t}>
                              {ENCOUNTER_TYPE_LABELS[t] ?? t}
                            </option>
                          ))}
                        </select>
                      </FormControl>
                      <FormMessage name={field.name} />
                    </FormItem>
                  )}
                />

                {/* Status */}
                <FormField
                  control={form.control}
                  name="status"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Status</FormLabel>
                      <FormControl>
                        <select
                          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                          value={field.value}
                          onChange={field.onChange}
                        >
                          {ENCOUNTER_STATUSES.map((s) => (
                            <option key={s} value={s}>
                              {STATUS_LABELS[s] ?? s}
                            </option>
                          ))}
                        </select>
                      </FormControl>
                      <FormMessage name={field.name} />
                    </FormItem>
                  )}
                />

                {/* Scheduled at */}
                <FormField
                  control={form.control}
                  name="scheduled_at"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Scheduled at</FormLabel>
                      <FormControl>
                        <Input type="datetime-local" {...field} />
                      </FormControl>
                      <FormMessage name={field.name} />
                    </FormItem>
                  )}
                />

                {/* Chief complaint */}
                <FormField
                  control={form.control}
                  name="chief_complaint"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Chief Complaint</FormLabel>
                      <FormControl>
                        <Textarea
                          placeholder="Patient's main concern"
                          {...field}
                          value={field.value ?? ""}
                        />
                      </FormControl>
                      <FormMessage name={field.name} />
                    </FormItem>
                  )}
                />

                {submitError ? (
                  <p className="text-sm text-red-600">
                    Failed to save encounter. Please try again.
                  </p>
                ) : null}

                <Button type="submit" className="w-full" disabled={isSubmitting}>
                  {isSubmitting
                    ? "Saving..."
                    : isEditMode
                      ? "Update Encounter"
                      : "Save Encounter"}
                </Button>
              </form>
            </Form>
          </SheetContent>
        </Sheet>
      </div>

      {/* Filters row */}
      <div className="flex flex-wrap items-center gap-3">
        <Input
          placeholder="Search by complaint or encounter ID"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
        <select
          className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All Statuses</option>
          {ENCOUNTER_STATUSES.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABELS[s] ?? s}
            </option>
          ))}
        </select>
      </div>

      {/* Loading / Error */}
      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading encounters...</p>
      ) : null}
      {isError ? (
        <p className="text-sm text-red-600">
          Error loading encounters:{" "}
          {(error as Error).message || "Unknown error"}
        </p>
      ) : null}

      {/* Table */}
      {!isLoading && !isError ? (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Encounter ID</TableHead>
                <TableHead>Patient</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Scheduled</TableHead>
                <TableHead>Chief Complaint</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {encounters.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={7}
                    className="text-center text-muted-foreground"
                  >
                    No encounters found.
                  </TableCell>
                </TableRow>
              ) : (
                encounters.map((enc) => (
                  <TableRow key={enc.id}>
                    <TableCell className="font-mono text-xs">
                      {enc.encounter_id}
                    </TableCell>
                    <TableCell>
                      <button
                        type="button"
                        className="font-medium hover:underline"
                        onClick={() => router.push(`/encounters/${enc.id}`)}
                      >
                        {getPatientName(enc)}
                      </button>
                    </TableCell>
                    <TableCell>
                      {ENCOUNTER_TYPE_LABELS[enc.encounter_type] ??
                        enc.encounter_type}
                    </TableCell>
                    <TableCell>
                      <Badge variant={STATUS_VARIANT[enc.status] ?? "secondary"}>
                        {STATUS_LABELS[enc.status] ?? enc.status}
                      </Badge>
                    </TableCell>
                    <TableCell>{formatDateTime(enc.scheduled_at)}</TableCell>
                    <TableCell className="max-w-[200px] truncate">
                      {enc.chief_complaint || "-"}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => router.push(`/encounters/${enc.id}`)}
                        >
                          Open
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openEditDrawer(enc)}
                        >
                          Edit
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-600 hover:text-red-700"
                          onClick={() => {
                            if (confirm("Delete this encounter?")) {
                              deleteMutation.mutate(enc.id);
                            }
                          }}
                        >
                          Delete
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      ) : null}
    </div>
  );
}
