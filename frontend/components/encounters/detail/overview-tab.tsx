"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useGenerateTriageSummary } from "@/lib/use-encounter-detail";
import type { PatientBackgroundDetail, PatientDetail, TriageAISummary } from "@/types/encounter-detail";
import type { Encounter } from "@/types/encounter-queue";
import {
  STATUS_COLOR,
  STATUS_LABEL,
  TYPE_LABEL,
} from "@/types/encounter-queue";
import {
  Activity,
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  Heart,
  Minus,
  Pill,
  Thermometer,
  Wind,
} from "lucide-react";

type Props = {
  encounter: Encounter;
  patientProfile?: PatientDetail | null;
  patientBackground?: PatientBackgroundDetail | null;
};

function formatDt(v: string | null | undefined): string {
  if (!v) return "-";
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function TrendArrow({ current, previous }: { current: number | null; previous: number | null }) {
  if (current == null || previous == null) return <Minus className="h-3 w-3 text-muted-foreground" />;
  if (current > previous) return <ArrowUp className="h-3 w-3 text-red-500" />;
  if (current < previous) return <ArrowDown className="h-3 w-3 text-blue-500" />;
  return <Minus className="h-3 w-3 text-muted-foreground" />;
}

function VitalCard({
  label,
  value,
  unit,
  icon: Icon,
  current,
  previous,
}: {
  label: string;
  value: string | null;
  unit: string;
  icon: React.ElementType;
  current: number | null;
  previous: number | null;
}) {
  if (value == null) return null;
  return (
    <div className="rounded-lg border p-3 space-y-1">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <div className="flex items-center gap-1.5">
        <span className="text-lg font-semibold">{value}</span>
        <span className="text-xs text-muted-foreground">{unit}</span>
        <TrendArrow current={current} previous={previous} />
      </div>
    </div>
  );
}

function formatDob(dob: string | null | undefined): string {
  if (!dob) return "-";
  const d = new Date(dob);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleDateString();
}

function parseCurrentMedications(raw: string | null | undefined): string[] {
  if (!raw) return [];
  return raw
    .split(/\r?\n|;/)
    .map((v) => v.trim())
    .filter(Boolean);
}

function stripHtml(value: string): string {
  return value.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function deriveChiefComplaint(encounter: Encounter): string | null {
  const direct = encounter.chief_complaint?.trim();
  if (direct) return direct;

  const recentNotes = [...encounter.notes].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  for (const note of recentNotes) {
    const fields = [note.subjective, note.objective, note.assessment, note.plan];
    for (const field of fields) {
      if (!field) continue;
      const text = stripHtml(field);
      if (!text) continue;

      const prefixed = text.match(/(?:chief\s*complaint|cc)\s*[:\-]\s*(.+)/i);
      if (prefixed?.[1]?.trim()) return prefixed[1].trim();
    }

    const subjective = note.subjective ? stripHtml(note.subjective) : "";
    if (subjective) return subjective;
  }

  return null;
}

export function OverviewTab({ encounter, patientProfile, patientBackground }: Props) {
  const latest = encounter.vitals[0] ?? null;
  const previous = encounter.vitals[1] ?? null;
  const chiefComplaint = deriveChiefComplaint(encounter);
  const [summary, setSummary] = useState<TriageAISummary | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const triageSummaryMutation = useGenerateTriageSummary(encounter.id);

  const patientMrn = patientProfile?.mrn ?? `MRN-${encounter.patient_id.slice(0, 8).toUpperCase()}`;
  const allergies: string[] = patientProfile?.allergies ?? [];
  const chronicConditions = encounter.diagnoses
    .filter((d) => d.is_chronic_condition)
    .map((d) => `${d.icd_code} — ${d.icd_description}`);
  const activeEncounterMeds = encounter.medications.map(
    (m) => `${m.drug_name} ${m.dosage} ${m.dosage_unit} ${m.frequency}`
  );
  const backgroundMeds = parseCurrentMedications(patientBackground?.current_medications);
  const activeMedications =
    activeEncounterMeds.length > 0 ? activeEncounterMeds : backgroundMeds;

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
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
      {/* Main content */}
      <div className="space-y-6">
        {/* Encounter header */}
        <div className="rounded-lg border p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">
              {encounter.patient
                ? `${encounter.patient.first_name} ${encounter.patient.last_name}`
                : "Unknown Patient"}
            </h3>
            <Badge
              variant="outline"
              className={`text-xs ${STATUS_COLOR[encounter.status] ?? ""}`}
            >
              {STATUS_LABEL[encounter.status] ?? encounter.status}
            </Badge>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div>
              <span className="text-muted-foreground">DOB</span>
              <p className="font-medium">{formatDob(patientProfile?.date_of_birth)}</p>
            </div>
            <div>
              <span className="text-muted-foreground">MRN</span>
              <p className="font-medium">{patientMrn}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Encounter ID</span>
              <p className="font-medium">{encounter.encounter_id}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Type</span>
              <p className="font-medium">
                {TYPE_LABEL[encounter.encounter_type] ?? encounter.encounter_type}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">Date</span>
              <p className="font-medium">{formatDt(encounter.scheduled_at || encounter.created_at)}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Provider</span>
              <p className="font-medium">{encounter.provider_id ?? "Unassigned"}</p>
            </div>
          </div>
          {chiefComplaint && (
            <div className="text-sm">
              <span className="text-muted-foreground">Chief Complaint</span>
              <p className="font-medium">{chiefComplaint}</p>
            </div>
          )}
        </div>

        {/* Vitals summary */}
        <div className="space-y-3 rounded-lg border p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h4 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                AI Triage Summary
              </h4>
              <p className="text-xs text-muted-foreground">
                Generates a clinician briefing from chief complaint, vitals, and prior history.
              </p>
            </div>
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
          </div>

          {summaryError && (
            <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {summaryError}
            </p>
          )}

          {summary ? (
            <div className="space-y-3">
              <p className="text-sm">{summary.summary}</p>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Focus Points
                </p>
                {summary.clinician_focus_points.length > 0 ? (
                  <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
                    {summary.clinician_focus_points.map((point, index) => (
                      <li key={`${point}-${index}`}>{point}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">No additional focus points.</p>
                )}
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Red Flags
                  </p>
                  {summary.red_flags.length > 0 ? (
                    <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-red-700">
                      {summary.red_flags.map((flag, index) => (
                        <li key={`${flag}-${index}`}>{flag}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-muted-foreground">No red flags detected from available data.</p>
                  )}
                </div>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Missing Information
                  </p>
                  {summary.missing_information.length > 0 ? (
                    <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
                      {summary.missing_information.map((item, index) => (
                        <li key={`${item}-${index}`}>{item}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-muted-foreground">No major documentation gaps detected.</p>
                  )}
                </div>
              </div>

              <p className="text-[11px] text-muted-foreground">
                Generated {formatDt(summary.generated_at)} using {summary.orchestration} ({summary.model_provider}/{summary.model_name})
              </p>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No summary generated yet.
            </p>
          )}
        </div>

        <div className="space-y-3">
          <h4 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Vitals Summary
          </h4>
          {latest ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              <VitalCard
                label="Blood Pressure"
                value={
                  latest.blood_pressure_systolic != null
                    ? `${latest.blood_pressure_systolic}/${latest.blood_pressure_diastolic}`
                    : null
                }
                unit="mmHg"
                icon={Activity}
                current={latest.blood_pressure_systolic}
                previous={previous?.blood_pressure_systolic ?? null}
              />
              <VitalCard
                label="Pulse"
                value={latest.pulse_rate != null ? String(latest.pulse_rate) : null}
                unit="bpm"
                icon={Heart}
                current={latest.pulse_rate}
                previous={previous?.pulse_rate ?? null}
              />
              <VitalCard
                label="Temperature"
                value={latest.temperature != null ? String(latest.temperature) : null}
                unit="°F"
                icon={Thermometer}
                current={latest.temperature}
                previous={previous?.temperature ?? null}
              />
              <VitalCard
                label="SpO₂"
                value={latest.oxygen_saturation != null ? String(latest.oxygen_saturation) : null}
                unit="%"
                icon={Wind}
                current={latest.oxygen_saturation}
                previous={previous?.oxygen_saturation ?? null}
              />
              <VitalCard
                label="Respiratory Rate"
                value={latest.respiratory_rate != null ? String(latest.respiratory_rate) : null}
                unit="/min"
                icon={Wind}
                current={latest.respiratory_rate}
                previous={previous?.respiratory_rate ?? null}
              />
              <VitalCard
                label="Pain Score"
                value={latest.pain_score != null ? `${latest.pain_score}/10` : null}
                unit=""
                icon={Activity}
                current={latest.pain_score}
                previous={previous?.pain_score ?? null}
              />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No vitals recorded</p>
          )}
          {latest && (
            <p className="text-xs text-muted-foreground">
              Recorded {formatDt(latest.recorded_at ?? latest.created_at)}
            </p>
          )}
        </div>
      </div>

      {/* Right sidebar */}
      <div className="space-y-4">
        {/* Allergies */}
        <div className="rounded-lg border p-3 space-y-2">
          <div className="flex items-center gap-1.5">
            <AlertTriangle className={`h-4 w-4 ${allergies.length > 0 ? "text-red-500" : "text-muted-foreground"}`} />
            <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Allergies
            </h4>
          </div>
          {allergies.length > 0 ? (
            <div className="space-y-1">
              <p className="text-xs font-medium text-red-700">Allergy alert: review before ordering.</p>
              {allergies.map((a, i) => (
                <Badge key={i} variant="outline" className="bg-red-50 text-red-700 border-red-300 text-xs mr-1">
                  {a}
                </Badge>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">No known allergies</p>
          )}
        </div>

        {/* Chronic conditions */}
        <div className="rounded-lg border p-3 space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Active Problems / Chronic Conditions
          </h4>
          {chronicConditions.length > 0 ? (
            <ScrollArea className="max-h-40">
              <ul className="space-y-1 text-sm">
                {chronicConditions.map((c, i) => (
                  <li key={i} className="text-sm">{c}</li>
                ))}
              </ul>
            </ScrollArea>
          ) : (
            <p className="text-xs text-muted-foreground">None documented</p>
          )}
        </div>

        {/* Current medications */}
        <div className="rounded-lg border p-3 space-y-2">
          <div className="flex items-center gap-1.5">
            <Pill className="h-4 w-4 text-muted-foreground" />
            <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Current Medications
            </h4>
          </div>
          {activeMedications.length > 0 ? (
            <ScrollArea className="max-h-40">
              <ul className="space-y-1">
                {activeMedications.map((m, i) => (
                  <li key={i} className="text-xs">{m}</li>
                ))}
              </ul>
            </ScrollArea>
          ) : (
            <p className="text-xs text-muted-foreground">No medications</p>
          )}
        </div>
      </div>
    </div>
  );
}
