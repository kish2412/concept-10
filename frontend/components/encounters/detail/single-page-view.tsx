"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useGenerateTriageSummary } from "@/lib/use-encounter-detail";
import type { PatientBackgroundDetail, PatientDetail, TriageAISummary } from "@/types/encounter-detail";
import type { Encounter } from "@/types/encounter-queue";
import { TYPE_LABEL } from "@/types/encounter-queue";
import { ClinicalNotesTab } from "@/components/encounters/detail/clinical-notes-tab";
import { DiagnosesTab } from "@/components/encounters/detail/diagnoses-tab";
import { OrdersTab } from "@/components/encounters/detail/orders-tab";
import { PrescriptionsTab } from "@/components/encounters/detail/prescriptions-tab";
import { DispositionTab } from "@/components/encounters/detail/disposition-tab";
import { ChevronDown, ChevronRight } from "lucide-react";

type Props = {
  encounter: Encounter;
  patientProfile?: PatientDetail | null;
  patientBackground?: PatientBackgroundDetail | null;
  readOnly: boolean;
  onDirtyNotesChange: (dirty: boolean) => void;
  onDirtyDispositionChange: (dirty: boolean) => void;
};

function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleDateString();
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function stripHtml(value: string): string {
  return value.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function deriveChiefComplaint(encounter: Encounter): string {
  const direct = encounter.chief_complaint?.trim();
  if (direct) return direct;

  const latestSoap = encounter.notes
    .slice()
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .find((note) => note.note_type === "SOAP");

  if (!latestSoap) return "-";

  const fields = [latestSoap.subjective, latestSoap.objective, latestSoap.assessment, latestSoap.plan];
  for (const field of fields) {
    if (!field) continue;
    const text = stripHtml(field);
    if (text) return text;
  }

  return "-";
}

function CollapsibleDrawer({
  title,
  defaultOpen = false,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className="rounded-lg border bg-background">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
        aria-expanded={open}
      >
        <h3 className="text-sm font-semibold">{title}</h3>
        {open ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        )}
      </button>
      <div className={open ? "border-t px-4 py-4" : "hidden border-t px-4 py-4"}>{children}</div>
    </section>
  );
}

function EmptyState({ label }: { label: string }) {
  return <p className="text-sm text-muted-foreground">{label}</p>;
}

function KeyValueGrid({ items }: { items: Array<{ label: string; value: string }> }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((item) => (
        <div key={item.label} className="rounded-md border bg-muted/20 px-3 py-2">
          <p className="text-xs text-muted-foreground">{item.label}</p>
          <p className="text-sm font-medium">{item.value}</p>
        </div>
      ))}
    </div>
  );
}

export function EncounterSinglePageView({
  encounter,
  patientProfile,
  patientBackground,
  readOnly,
  onDirtyNotesChange,
  onDirtyDispositionChange,
}: Props) {
  const chiefComplaint = useMemo(() => deriveChiefComplaint(encounter), [encounter]);
  const [summary, setSummary] = useState<TriageAISummary | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const triageSummaryMutation = useGenerateTriageSummary(encounter.id);
  const patientName = encounter.patient
    ? `${encounter.patient.first_name} ${encounter.patient.last_name}`
    : "Unknown Patient";

  const basicPatientDetails = [
    { label: "Patient", value: patientName },
    { label: "Encounter ID", value: encounter.encounter_id },
    { label: "Encounter Type", value: TYPE_LABEL[encounter.encounter_type] ?? encounter.encounter_type },
    { label: "DOB", value: formatDate(patientProfile?.date_of_birth) },
    { label: "MRN", value: patientProfile?.mrn ?? `MRN-${encounter.patient_id.slice(0, 8).toUpperCase()}` },
    { label: "Scheduled", value: formatDateTime(encounter.scheduled_at || encounter.created_at) },
  ];

  const morePatientDetails = [
    { label: "Provider", value: encounter.provider_id ?? "Unassigned" },
    { label: "Checked In", value: formatDateTime(encounter.checked_in_at) },
    { label: "Started", value: formatDateTime(encounter.started_at) },
    { label: "Ended", value: formatDateTime(encounter.ended_at) },
  ];

  const allergies = patientProfile?.allergies ?? [];
  const chronicConditions = patientProfile?.chronic_conditions ?? [];
  const currentMeds = patientProfile?.current_medications ?? [];

  const handleGenerateSummary = async (regenerate: boolean) => {
    setSummaryError(null);
    try {
      const result = await triageSummaryMutation.mutateAsync(regenerate);
      setSummary(result);
    } catch (error) {
      const detail =
        typeof error === "object" &&
        error !== null &&
        "response" in error &&
        typeof error.response === "object" &&
        error.response !== null &&
        "data" in error.response &&
        typeof error.response.data === "object" &&
        error.response.data !== null &&
        "detail" in error.response.data
          ? String(error.response.data.detail)
          : "Unable to generate triage summary right now.";
      setSummaryError(detail);
    }
  };

  return (
    <div className="space-y-4">
      <CollapsibleDrawer title="Basic Patient Details" defaultOpen>
        <KeyValueGrid items={basicPatientDetails} />
      </CollapsibleDrawer>

      <CollapsibleDrawer title="Patient More Details">
        <KeyValueGrid items={morePatientDetails} />
        <div className="mt-4 space-y-3">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Allergies</p>
            {allergies.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {allergies.map((item) => (
                  <Badge key={item} variant="outline" className="bg-red-50 text-red-700 border-red-300">
                    {item}
                  </Badge>
                ))}
              </div>
            ) : (
              <EmptyState label="No known allergies" />
            )}
          </div>

          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Chronic Conditions</p>
            {chronicConditions.length > 0 ? (
              <ul className="list-disc space-y-1 pl-5 text-sm">
                {chronicConditions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <EmptyState label="No chronic conditions documented" />
            )}
          </div>

          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Current Medications</p>
            {currentMeds.length > 0 ? (
              <ul className="list-disc space-y-1 pl-5 text-sm">
                {currentMeds.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <EmptyState label="No current medications documented" />
            )}
          </div>
        </div>
      </CollapsibleDrawer>

      <CollapsibleDrawer title="Background Information" defaultOpen>
        <div className="space-y-4">
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Medical History</p>
            <p className="text-sm">{patientBackground?.medical_history || "-"}</p>
          </div>
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Surgical History</p>
            <p className="text-sm">{patientBackground?.surgical_history || "-"}</p>
          </div>
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Family History</p>
            <p className="text-sm">{patientBackground?.family_history || "-"}</p>
          </div>
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Social History</p>
            <p className="text-sm">{patientBackground?.social_history || "-"}</p>
          </div>
        </div>
      </CollapsibleDrawer>

      <CollapsibleDrawer title="Patient Complains and Clinical Notes" defaultOpen>
        <div className="mb-4 rounded-md border bg-muted/20 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Chief Complaint</p>
          <p className="mt-1 text-sm">{chiefComplaint}</p>
        </div>
        <ClinicalNotesTab
          encounter={encounter}
          readOnly={readOnly}
          onDirtyChange={onDirtyNotesChange}
        />
      </CollapsibleDrawer>

      <CollapsibleDrawer title="AI Triage Summary" defaultOpen>
        <div className="space-y-3">
          <Button
            type="button"
            size="sm"
            onClick={() => handleGenerateSummary(Boolean(summary))}
            disabled={triageSummaryMutation.isPending}
          >
            {triageSummaryMutation.isPending
              ? "Generating..."
              : summary
                ? "Regenerate"
                : "Generate Summary"}
          </Button>

          {summaryError && (
            <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {summaryError}
            </p>
          )}

          {summary ? (
            <div className="space-y-3">
              <p className="text-sm">{summary.summary}</p>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Focus Points</p>
                <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
                  {summary.clinician_focus_points.map((item, index) => (
                    <li key={`${item}-${index}`}>{item}</li>
                  ))}
                </ul>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Missing Information</p>
                {summary.missing_information.length > 0 ? (
                  <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
                    {summary.missing_information.map((item, index) => (
                      <li key={`${item}-${index}`}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <EmptyState label="No major documentation gaps detected" />
                )}
              </div>
            </div>
          ) : (
            <EmptyState label="No summary generated yet" />
          )}
        </div>
      </CollapsibleDrawer>

      <CollapsibleDrawer title="Diagnosis">
        <DiagnosesTab encounter={encounter} readOnly={readOnly} />
      </CollapsibleDrawer>

      <CollapsibleDrawer title="Orders">
        <OrdersTab encounter={encounter} readOnly={readOnly} />
      </CollapsibleDrawer>

      <CollapsibleDrawer title="Medications">
        <PrescriptionsTab encounter={encounter} readOnly={readOnly} />
      </CollapsibleDrawer>

      <CollapsibleDrawer title="Disposition">
        <DispositionTab
          encounter={encounter}
          readOnly={readOnly}
          onDirtyChange={onDirtyDispositionChange}
        />
      </CollapsibleDrawer>
    </div>
  );
}
