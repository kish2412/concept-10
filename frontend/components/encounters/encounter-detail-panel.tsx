"use client";

import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { useEncounterDetail } from "@/lib/use-encounter-queue";
import type { Encounter } from "@/types/encounter-queue";
import {
  STATUS_COLOR,
  STATUS_LABEL,
  TYPE_LABEL,
} from "@/types/encounter-queue";

type Props = {
  encounterId: string | null;
  open: boolean;
  onClose: () => void;
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h4>
      {children}
    </div>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[120px_1fr] gap-1 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span>{value || "-"}</span>
    </div>
  );
}

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

export function EncounterDetailPanel({ encounterId, open, onClose }: Props) {
  const { data: enc, isLoading } = useEncounterDetail(open ? encounterId : null);

  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent className="w-full sm:max-w-lg p-0">
        <SheetHeader className="border-b px-6 py-4">
          <SheetTitle className="flex items-center gap-2">
            Encounter Detail
            {enc ? (
              <Badge variant="outline" className={`text-xs ${STATUS_COLOR[enc.status] ?? ""}`}>
                {STATUS_LABEL[enc.status] ?? enc.status}
              </Badge>
            ) : null}
          </SheetTitle>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-80px)]">
          <div className="space-y-6 px-6 py-4">
            {isLoading || !enc ? (
              <>
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="h-5 w-1/2" />
                <Skeleton className="h-40 w-full" />
              </>
            ) : (
              <>
                {/* Overview */}
                <Section title="Overview">
                  <Field label="Encounter ID" value={enc.encounter_id} />
                  <Field
                    label="Patient"
                    value={
                      enc.patient
                        ? `${enc.patient.first_name} ${enc.patient.last_name}`
                        : enc.patient_id
                    }
                  />
                  <Field
                    label="Type"
                    value={
                      <Badge variant="outline" className="text-[10px]">
                        {TYPE_LABEL[enc.encounter_type] ?? enc.encounter_type}
                      </Badge>
                    }
                  />
                  <Field label="Chief Complaint" value={enc.chief_complaint} />
                  <Field label="Scheduled" value={formatDt(enc.scheduled_at)} />
                  <Field label="Checked-In" value={formatDt(enc.checked_in_at)} />
                  <Field label="Started" value={formatDt(enc.started_at)} />
                  <Field label="Ended" value={formatDt(enc.ended_at)} />
                </Section>

                {/* Vitals */}
                {enc.vitals.length > 0 ? (
                  <Section title="Latest Vitals">
                    {(() => {
                      const v = enc.vitals[0];
                      return (
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                          {v.blood_pressure_systolic != null && (
                            <Field label="BP" value={`${v.blood_pressure_systolic}/${v.blood_pressure_diastolic}`} />
                          )}
                          {v.pulse_rate != null && <Field label="Pulse" value={`${v.pulse_rate} bpm`} />}
                          {v.temperature != null && <Field label="Temp" value={`${v.temperature}°`} />}
                          {v.oxygen_saturation != null && <Field label="SpO₂" value={`${v.oxygen_saturation}%`} />}
                          {v.respiratory_rate != null && <Field label="Resp Rate" value={`${v.respiratory_rate}`} />}
                          {v.pain_score != null && <Field label="Pain" value={`${v.pain_score}/10`} />}
                        </div>
                      );
                    })()}
                  </Section>
                ) : null}

                {/* Notes */}
                {enc.notes.length > 0 ? (
                  <Section title={`Notes (${enc.notes.length})`}>
                    {enc.notes.map((note) => (
                      <div key={note.id} className="rounded border p-3 text-sm space-y-1">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-[10px]">
                            {note.note_type}
                          </Badge>
                          {note.is_signed && (
                            <Badge variant="outline" className="bg-green-50 text-green-700 text-[10px]">
                              Signed
                            </Badge>
                          )}
                          <span className="ml-auto text-xs text-muted-foreground">
                            {formatDt(note.created_at)}
                          </span>
                        </div>
                        {note.subjective && <p><strong>S:</strong> {note.subjective}</p>}
                        {note.objective && <p><strong>O:</strong> {note.objective}</p>}
                        {note.assessment && <p><strong>A:</strong> {note.assessment}</p>}
                        {note.plan && <p><strong>P:</strong> {note.plan}</p>}
                      </div>
                    ))}
                  </Section>
                ) : null}

                {/* Diagnoses */}
                {enc.diagnoses.length > 0 ? (
                  <Section title={`Diagnoses (${enc.diagnoses.length})`}>
                    {enc.diagnoses.map((dx) => (
                      <div key={dx.id} className="flex items-center gap-2 text-sm">
                        <Badge variant="outline" className="text-[10px]">{dx.icd_code}</Badge>
                        <span>{dx.icd_description}</span>
                        <Badge variant="outline" className="ml-auto text-[10px]">{dx.diagnosis_type}</Badge>
                      </div>
                    ))}
                  </Section>
                ) : null}

                {/* Orders */}
                {enc.orders.length > 0 ? (
                  <Section title={`Orders (${enc.orders.length})`}>
                    {enc.orders.map((order) => (
                      <div key={order.id} className="flex items-center gap-2 text-sm">
                        <Badge variant="outline" className="text-[10px]">{order.order_type}</Badge>
                        <span className="truncate">{order.order_description}</span>
                        <Badge variant="outline" className="ml-auto text-[10px]">{order.status}</Badge>
                      </div>
                    ))}
                  </Section>
                ) : null}

                {/* Medications */}
                {enc.medications.length > 0 ? (
                  <Section title={`Medications (${enc.medications.length})`}>
                    {enc.medications.map((med) => (
                      <div key={med.id} className="text-sm">
                        <p className="font-medium">{med.drug_name}</p>
                        <p className="text-xs text-muted-foreground">
                          {med.dosage} {med.dosage_unit} — {med.frequency} — {med.route}
                        </p>
                      </div>
                    ))}
                  </Section>
                ) : null}

                {/* Disposition */}
                {enc.disposition ? (
                  <Section title="Disposition">
                    <Field label="Type" value={enc.disposition.disposition_type} />
                    <Field
                      label="Follow-up"
                      value={
                        enc.disposition.follow_up_required
                          ? `In ${enc.disposition.follow_up_in_days ?? "?"} days`
                          : "None"
                      }
                    />
                    {enc.disposition.discharge_instructions && (
                      <Field label="Instructions" value={enc.disposition.discharge_instructions} />
                    )}
                  </Section>
                ) : null}
              </>
            )}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
