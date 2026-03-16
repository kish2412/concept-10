"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EncounterCard } from "./encounter-card";
import type { Encounter, EncounterStatus } from "@/types/encounter-queue";
import {
  QUEUE_STATUSES,
  STATUS_COLOR,
  STATUS_LABEL,
} from "@/types/encounter-queue";

type Props = {
  encounters: Encounter[];
  isLoading: boolean;
  onStatusChange: (encounterId: string, newStatus: EncounterStatus) => void;
  onView: (encounter: Encounter) => void;
  onMoveNext: (encounter: Encounter) => void;
};

export function KanbanBoard({
  encounters,
  isLoading,
  onStatusChange,
  onView,
  onMoveNext,
}: Props) {
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [overStatus, setOverStatus] = useState<EncounterStatus | null>(null);

  const columns = useMemo(() => {
    const map = new Map<string, Encounter[]>();
    for (const s of QUEUE_STATUSES) map.set(s, []);
    for (const enc of encounters) {
      const col = map.get(enc.status);
      if (col) col.push(enc);
    }
    return map;
  }, [encounters]);

  function handleDragStart(encounterId: string) {
    setDraggedId(encounterId);
  }

  function handleDragEnd() {
    setDraggedId(null);
    setOverStatus(null);
  }

  function handleDrop(targetStatus: EncounterStatus) {
    if (!draggedId) {
      return;
    }

    const encounter = encounters.find((item) => item.id === draggedId);
    if (encounter && encounter.status !== targetStatus) {
      onStatusChange(draggedId, targetStatus);
    }

    handleDragEnd();
  }

  if (isLoading) {
    return (
      <div className="flex gap-4 overflow-x-auto p-4">
        {QUEUE_STATUSES.map((s) => (
          <div key={s} className="w-72 shrink-0 space-y-3">
            <Skeleton className="h-8 w-full rounded" />
            <Skeleton className="h-28 w-full rounded-lg" />
            <Skeleton className="h-28 w-full rounded-lg" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="flex min-h-full gap-3 overflow-x-auto p-3 sm:gap-4 sm:p-4">
      {QUEUE_STATUSES.map((status) => {
        const items = columns.get(status) ?? [];
        const isOver = overStatus === status;

        return (
          <div
            key={status}
            className={`flex h-full w-60 shrink-0 flex-col rounded-lg p-1 transition-colors sm:w-64 md:w-72 ${isOver ? "bg-muted/50" : ""}`}
            onDragOver={(event) => {
              event.preventDefault();
              if (draggedId) {
                setOverStatus(status);
              }
            }}
            onDragEnter={(event) => {
              event.preventDefault();
              if (draggedId) {
                setOverStatus(status);
              }
            }}
            onDragLeave={() => {
              if (overStatus === status) {
                setOverStatus(null);
              }
            }}
            onDrop={(event) => {
              event.preventDefault();
              handleDrop(status);
            }}
          >
            <div className="mb-3 flex items-center gap-2">
              <Badge
                variant="outline"
                className={`${STATUS_COLOR[status] ?? ""} text-xs`}
              >
                {STATUS_LABEL[status]}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {items.length}
              </span>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto pr-2">
              <div className="space-y-2 pr-2">
                {items.length === 0 ? (
                  <p className="py-8 text-center text-xs text-muted-foreground">
                    No encounters
                  </p>
                ) : (
                  items.map((enc) => (
                    <div
                      key={enc.id}
                      draggable
                      className={`cursor-grab active:cursor-grabbing ${draggedId === enc.id ? "opacity-40" : "opacity-100"}`}
                      onDragStart={(event) => {
                        event.dataTransfer.effectAllowed = "move";
                        event.dataTransfer.setData("text/plain", enc.id);
                        handleDragStart(enc.id);
                      }}
                      onDragEnd={handleDragEnd}
                    >
                      <EncounterCard
                        encounter={enc}
                        onView={onView}
                        onMoveNext={onMoveNext}
                        compact
                      />
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
