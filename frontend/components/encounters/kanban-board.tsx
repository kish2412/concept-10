"use client";

import { useMemo } from "react";
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EncounterCard } from "./encounter-card";
import { DroppableColumn, SortableEncounterCard } from "./kanban-primitives";
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
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor)
  );

  const columns = useMemo(() => {
    const map = new Map<string, Encounter[]>();
    for (const s of QUEUE_STATUSES) map.set(s, []);
    for (const enc of encounters) {
      const col = map.get(enc.status);
      if (col) col.push(enc);
    }
    return map;
  }, [encounters]);

  const activeEncounter = useMemo(
    () => encounters.find((e) => e.id === activeId) ?? null,
    [encounters, activeId]
  );

  function handleDragStart(event: DragStartEvent) {
    setActiveId(event.active.id as string);
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveId(null);
    const { active, over } = event;
    if (!over) return;

    const encId = active.id as string;
    // The droppable id is the status column id
    let targetStatus: string | null = null;

    if (QUEUE_STATUSES.includes(over.id as EncounterStatus)) {
      targetStatus = over.id as string;
    } else {
      // Dropped on another card — find which column it belongs to
      const targetEnc = encounters.find((e) => e.id === over.id);
      if (targetEnc) targetStatus = targetEnc.status;
    }

    if (targetStatus) {
      const enc = encounters.find((e) => e.id === encId);
      if (enc && enc.status !== targetStatus) {
        onStatusChange(encId, targetStatus as EncounterStatus);
      }
    }
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
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-3 overflow-x-auto p-3 sm:gap-4 sm:p-4">
        {QUEUE_STATUSES.map((status) => {
          const items = columns.get(status) ?? [];
          return (
            <DroppableColumn key={status} id={status}>
              <div className="w-60 shrink-0 sm:w-64 md:w-72">
                {/* Column header */}
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

                {/* Cards */}
                <ScrollArea className="h-[calc(100vh-220px)]">
                  <SortableContext
                    items={items.map((e) => e.id)}
                    strategy={verticalListSortingStrategy}
                  >
                    <div className="space-y-2 pr-2">
                      {items.length === 0 ? (
                        <p className="py-8 text-center text-xs text-muted-foreground">
                          No encounters
                        </p>
                      ) : (
                        items.map((enc) => (
                          <SortableEncounterCard key={enc.id} id={enc.id}>
                            <EncounterCard
                              encounter={enc}
                              onView={onView}
                              onMoveNext={onMoveNext}
                              compact
                            />
                          </SortableEncounterCard>
                        ))
                      )}
                    </div>
                  </SortableContext>
                </ScrollArea>
              </div>
            </DroppableColumn>
          );
        })}
      </div>

      <DragOverlay>
        {activeEncounter ? (
          <div className="w-72 opacity-90">
            <EncounterCard
              encounter={activeEncounter}
              onView={() => {}}
              onMoveNext={() => {}}
              compact
            />
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
