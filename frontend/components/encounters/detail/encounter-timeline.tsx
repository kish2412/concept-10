"use client";

import { ScrollArea } from "@/components/ui/scroll-area";
import type { Encounter } from "@/types/encounter-queue";
import { STATUS_LABEL } from "@/types/encounter-queue";
import {
  Activity,
  CheckCircle,
  ClipboardList,
  Clock,
  FileText,
  LogIn,
  Pill,
  Stethoscope,
} from "lucide-react";

type Props = {
  encounter: Encounter;
};

type TimelineEvent = {
  icon: React.ElementType;
  label: string;
  timestamp: string;
  detail?: string;
  color: string;
};

export function EncounterTimeline({ encounter }: Props) {
  // Build timeline from encounter data
  const events: TimelineEvent[] = [];

  // Encounter creation
  events.push({
    icon: Clock,
    label: "Encounter created",
    timestamp: encounter.created_at,
    detail: encounter.encounter_id,
    color: "text-slate-500",
  });

  // Status transitions
  if (encounter.scheduled_at) {
    events.push({
      icon: Clock,
      label: "Scheduled",
      timestamp: encounter.scheduled_at,
      color: "text-blue-500",
    });
  }
  if (encounter.checked_in_at) {
    events.push({
      icon: LogIn,
      label: "Checked in",
      timestamp: encounter.checked_in_at,
      color: "text-blue-600",
    });
  }
  if (encounter.triage_at) {
    events.push({
      icon: Activity,
      label: "Triage",
      timestamp: encounter.triage_at,
      color: "text-yellow-600",
    });
  }
  if (encounter.started_at) {
    events.push({
      icon: Stethoscope,
      label: "Consultation started",
      timestamp: encounter.started_at,
      color: "text-green-600",
    });
  }

  // Vitals recordings
  for (const v of encounter.vitals) {
    events.push({
      icon: Activity,
      label: "Vitals recorded",
      timestamp: v.recorded_at ?? v.created_at,
      detail: [
        v.blood_pressure_systolic != null ? `BP ${v.blood_pressure_systolic}/${v.blood_pressure_diastolic}` : null,
        v.pulse_rate != null ? `HR ${v.pulse_rate}` : null,
        v.temperature != null ? `T ${v.temperature}°` : null,
      ]
        .filter(Boolean)
        .join(", "),
      color: "text-teal-500",
    });
  }

  // Notes
  for (const n of encounter.notes) {
    events.push({
      icon: FileText,
      label: n.is_signed ? `Note signed (v${n.version})` : `Note added (${n.note_type})`,
      timestamp: n.is_signed ? (n.signed_at ?? n.created_at) : n.created_at,
      color: n.is_signed ? "text-green-600" : "text-blue-500",
    });
  }

  // Orders
  for (const o of encounter.orders) {
    events.push({
      icon: ClipboardList,
      label: `${o.order_type} order: ${o.order_description.substring(0, 40)}`,
      timestamp: o.ordered_at ?? o.created_at,
      detail: `Status: ${o.status}${o.priority === "STAT" ? " (STAT)" : ""}`,
      color: o.priority === "STAT" ? "text-red-600" : "text-orange-500",
    });
  }

  // Medications
  for (const m of encounter.medications) {
    events.push({
      icon: Pill,
      label: `Rx: ${m.drug_name} ${m.dosage}${m.dosage_unit}`,
      timestamp: m.prescribed_at ?? m.created_at,
      color: "text-purple-500",
    });
  }

  // Disposition / discharge
  if (encounter.disposition) {
    events.push({
      icon: CheckCircle,
      label: `Disposition: ${encounter.disposition.disposition_type}`,
      timestamp: encounter.disposition.discharged_at ?? encounter.disposition.created_at,
      color: "text-green-700",
    });
  }
  if (encounter.ended_at) {
    events.push({
      icon: CheckCircle,
      label: "Encounter ended",
      timestamp: encounter.ended_at,
      color: "text-gray-600",
    });
  }

  // Sort by timestamp DESC
  events.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground px-1">
        Timeline
      </h4>
      <ScrollArea className="h-[calc(100vh-220px)]">
        <div className="space-y-0 px-1">
          {events.map((event, i) => {
            const Icon = event.icon;
            return (
              <div key={i} className="flex gap-2.5 pb-4 relative">
                {/* Vertical line */}
                {i < events.length - 1 && (
                  <div className="absolute left-[9px] top-5 bottom-0 w-px bg-border" />
                )}
                <div className={`shrink-0 mt-0.5 ${event.color}`}>
                  <Icon className="h-[18px] w-[18px]" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium leading-tight truncate">
                    {event.label}
                  </p>
                  {event.detail && (
                    <p className="text-[10px] text-muted-foreground truncate">
                      {event.detail}
                    </p>
                  )}
                  <p className="text-[10px] text-muted-foreground">
                    {new Date(event.timestamp).toLocaleString(undefined, {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
              </div>
            );
          })}
          {events.length === 0 && (
            <p className="text-xs text-muted-foreground py-4">No events</p>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
