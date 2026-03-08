"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { Encounter, EncounterStatus } from "@/types/encounter-queue";
import {
  NEXT_STATUS,
  STATUS_COLOR,
  STATUS_LABEL,
  TYPE_LABEL,
} from "@/types/encounter-queue";
import {
  ArrowRight,
  ChevronRight,
  Clock,
  Eye,
  UserPlus,
} from "lucide-react";
import { cn } from "@/lib/utils";

type Props = {
  encounter: Encounter;
  onView: (encounter: Encounter) => void;
  onMoveNext: (encounter: Encounter) => void;
  onAssign?: (encounter: Encounter) => void;
  compact?: boolean;
};

function getPatientName(enc: Encounter): string {
  if (enc.patient) return `${enc.patient.first_name} ${enc.patient.last_name}`;
  return enc.patient_id.slice(0, 8);
}

function getElapsedMs(enc: Encounter): number {
  const ref = enc.checked_in_at ?? enc.created_at;
  return Date.now() - new Date(ref).getTime();
}

function formatElapsed(ms: number): string {
  if (ms < 0) return "0m";
  const mins = Math.floor(ms / 60_000);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ${mins % 60}m`;
}

const WAIT_ALERT_MS = 30 * 60_000; // 30 minutes

export function EncounterCard({ encounter, onView, onMoveNext, onAssign, compact }: Props) {
  const [elapsed, setElapsed] = useState(() => getElapsedMs(encounter));

  useEffect(() => {
    const id = setInterval(() => setElapsed(getElapsedMs(encounter)), 30_000);
    return () => clearInterval(id);
  }, [encounter]);

  const isAlert = elapsed >= WAIT_ALERT_MS && encounter.status !== "DISCHARGED";
  const nextStatus = NEXT_STATUS[encounter.status as EncounterStatus];

  return (
    <TooltipProvider delayDuration={200}>
      <div
        className={cn(
          "group rounded-lg border bg-background p-3 shadow-sm transition-shadow hover:shadow-md",
          isAlert && "border-red-400 ring-1 ring-red-200",
          compact && "p-2"
        )}
      >
        {/* Top row: patient name + type badge */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{getPatientName(encounter)}</p>
            <p className="text-xs text-muted-foreground">{encounter.encounter_id}</p>
          </div>
          <Badge variant="outline" className={`shrink-0 text-[10px] ${STATUS_COLOR[encounter.encounter_type] || ""}`}>
            {TYPE_LABEL[encounter.encounter_type] ?? encounter.encounter_type}
          </Badge>
        </div>

        {/* Chief complaint */}
        {encounter.chief_complaint ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <p className="mt-1.5 line-clamp-1 text-xs text-muted-foreground cursor-default">
                {encounter.chief_complaint}
              </p>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-xs text-xs">
              {encounter.chief_complaint}
            </TooltipContent>
          </Tooltip>
        ) : null}

        {/* Status + timer row */}
        <div className="mt-2 flex items-center gap-2">
          <Badge variant="outline" className={`text-[10px] ${STATUS_COLOR[encounter.status] ?? ""}`}>
            {STATUS_LABEL[encounter.status] ?? encounter.status}
          </Badge>
          <span
            className={cn(
              "ml-auto flex items-center gap-1 text-xs tabular-nums",
              isAlert ? "font-semibold text-red-600" : "text-muted-foreground"
            )}
          >
            <Clock className="h-3 w-3" />
            {formatElapsed(elapsed)}
          </span>
        </div>

        {/* Actions */}
        <div className="mt-2 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button size="sm" variant="ghost" className="h-7 px-2" onClick={() => onView(encounter)}>
                <Eye className="h-3.5 w-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>View details</TooltipContent>
          </Tooltip>

          {nextStatus ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button size="sm" variant="ghost" className="h-7 px-2" onClick={() => onMoveNext(encounter)}>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Move to {STATUS_LABEL[nextStatus]}</TooltipContent>
            </Tooltip>
          ) : null}

          {onAssign ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button size="sm" variant="ghost" className="h-7 px-2" onClick={() => onAssign(encounter)}>
                  <UserPlus className="h-3.5 w-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Assign provider</TooltipContent>
            </Tooltip>
          ) : null}
        </div>
      </div>
    </TooltipProvider>
  );
}
