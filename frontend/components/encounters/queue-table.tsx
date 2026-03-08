"use client";

import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
import { ArrowRight, ArrowUpDown, Clock, Eye } from "lucide-react";
import { cn } from "@/lib/utils";

type SortKey = "patient" | "status" | "type" | "elapsed" | "complaint";
type SortDir = "asc" | "desc";

type Props = {
  encounters: Encounter[];
  isLoading: boolean;
  onView: (encounter: Encounter) => void;
  onMoveNext: (encounter: Encounter) => void;
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

const WAIT_ALERT_MS = 30 * 60_000;

export function QueueTable({ encounters, isLoading, onView, onMoveNext }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("elapsed");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [, setTick] = useState(0);

  // Refresh elapsed times every 30s
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 30_000);
    return () => clearInterval(id);
  }, []);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  const sorted = useMemo(() => {
    const list = [...encounters];
    const dir = sortDir === "asc" ? 1 : -1;
    list.sort((a, b) => {
      switch (sortKey) {
        case "patient":
          return dir * getPatientName(a).localeCompare(getPatientName(b));
        case "status":
          return dir * a.status.localeCompare(b.status);
        case "type":
          return dir * a.encounter_type.localeCompare(b.encounter_type);
        case "elapsed":
          return dir * (getElapsedMs(a) - getElapsedMs(b));
        case "complaint":
          return dir * (a.chief_complaint ?? "").localeCompare(b.chief_complaint ?? "");
        default:
          return 0;
      }
    });
    return list;
  }, [encounters, sortKey, sortDir]);

  function SortHeader({ label, sKey }: { label: string; sKey: SortKey }) {
    return (
      <Button
        variant="ghost"
        size="sm"
        className="-ml-3 h-8 px-2 text-xs font-medium"
        onClick={() => toggleSort(sKey)}
      >
        {label}
        <ArrowUpDown className="ml-1 h-3 w-3" />
      </Button>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-2 p-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full rounded" />
        ))}
      </div>
    );
  }

  return (
    <TooltipProvider delayDuration={200}>
      <div className="overflow-x-auto p-2 sm:p-4">
        <Table className="min-w-[700px]">
          <TableHeader>
            <TableRow>
              <TableHead className="w-[180px]">
                <SortHeader label="Patient" sKey="patient" />
              </TableHead>
              <TableHead className="w-[120px]">Encounter ID</TableHead>
              <TableHead className="w-[110px]">
                <SortHeader label="Type" sKey="type" />
              </TableHead>
              <TableHead className="w-[130px]">
                <SortHeader label="Status" sKey="status" />
              </TableHead>
              <TableHead className="w-[200px]">
                <SortHeader label="Chief Complaint" sKey="complaint" />
              </TableHead>
              <TableHead className="w-[90px]">
                <SortHeader label="Wait" sKey="elapsed" />
              </TableHead>
              <TableHead className="w-[100px] text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="py-12 text-center text-muted-foreground">
                  No encounters in queue
                </TableCell>
              </TableRow>
            ) : (
              sorted.map((enc) => {
                const elapsedMs = getElapsedMs(enc);
                const isAlert = elapsedMs >= WAIT_ALERT_MS && enc.status !== "DISCHARGED";
                const nextStatus = NEXT_STATUS[enc.status as EncounterStatus];

                return (
                  <TableRow
                    key={enc.id}
                    className={cn(isAlert && "bg-red-50/50")}
                  >
                    <TableCell className="font-medium">
                      {getPatientName(enc)}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {enc.encounter_id}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-[10px]">
                        {TYPE_LABEL[enc.encounter_type] ?? enc.encounter_type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={`text-[10px] ${STATUS_COLOR[enc.status] ?? ""}`}
                      >
                        {STATUS_LABEL[enc.status] ?? enc.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {enc.chief_complaint ? (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="line-clamp-1 max-w-[200px] cursor-default text-xs text-muted-foreground">
                              {enc.chief_complaint}
                            </span>
                          </TooltipTrigger>
                          <TooltipContent side="bottom" className="max-w-xs text-xs">
                            {enc.chief_complaint}
                          </TooltipContent>
                        </Tooltip>
                      ) : (
                        <span className="text-xs text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <span
                        className={cn(
                          "flex items-center gap-1 text-xs tabular-nums",
                          isAlert ? "font-semibold text-red-600" : "text-muted-foreground"
                        )}
                      >
                        <Clock className="h-3 w-3" />
                        {formatElapsed(elapsedMs)}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-7 px-2"
                              onClick={() => onView(enc)}
                            >
                              <Eye className="h-3.5 w-3.5" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>View details</TooltipContent>
                        </Tooltip>
                        {nextStatus ? (
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 px-2"
                                onClick={() => onMoveNext(enc)}
                              >
                                <ArrowRight className="h-3.5 w-3.5" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                              Move to {STATUS_LABEL[nextStatus]}
                            </TooltipContent>
                          </Tooltip>
                        ) : null}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>
    </TooltipProvider>
  );
}
