"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { QueueStatsBar } from "@/components/encounters/queue-stats-bar";
import { QueueFilterPanel } from "@/components/encounters/queue-filter-panel";
import { KanbanBoard } from "@/components/encounters/kanban-board";
import { QueueTable } from "@/components/encounters/queue-table";
import {
  useEncounterQueue,
  useTodaySummary,
  useUpdateEncounterStatus,
  useExportQueueCsv,
} from "@/lib/use-encounter-queue";
import type { Encounter, EncounterStatus, QueueFilters } from "@/types/encounter-queue";
import { NEXT_STATUS } from "@/types/encounter-queue";

const defaultFilters: QueueFilters = {
  search: "",
  status: "",
  encounter_type: "",
  provider_id: "",
  department_id: "",
};

export default function QueueDashboardPage() {
  // ── State ──
  const router = useRouter();
  const [filters, setFilters] = useState<QueueFilters>(defaultFilters);
  const [viewMode, setViewMode] = useState<"kanban" | "table">("kanban");

  // ── Data ──
  const { data: queueData, isLoading: queueLoading } = useEncounterQueue(filters);
  const { data: summary, isLoading: summaryLoading } = useTodaySummary();
  const statusMutation = useUpdateEncounterStatus();
  const exportCsv = useExportQueueCsv();

  const encounters = useMemo(() => queueData?.items ?? [], [queueData?.items]);

  // ── Handlers ──
  function handleView(enc: Encounter) {
    router.push(`/encounters/${enc.id}`);
  }

  function handleMoveNext(enc: Encounter) {
    const next = NEXT_STATUS[enc.status as EncounterStatus];
    if (next) {
      statusMutation.mutate({ id: enc.id, status: next });
    }
  }

  function handleStatusChange(encId: string, newStatus: EncounterStatus) {
    statusMutation.mutate({ id: encId, status: newStatus });
  }

  function handleSearchChange(value: string) {
    setFilters((f) => ({ ...f, search: value }));
  }

  function handleExport() {
    exportCsv(encounters);
  }

  const [filtersOpen, setFiltersOpen] = useState(false);

  // ── Render ──
  return (
    <div className="-m-4 md:-m-6 flex h-[calc(100vh-0px)] flex-col">
      {/* Top stats bar */}
      <QueueStatsBar
        summary={summary}
        isLoading={summaryLoading}
        search={filters.search}
        onSearchChange={handleSearchChange}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onExport={handleExport}
        onToggleFilters={() => setFiltersOpen((o) => !o)}
        filtersOpen={filtersOpen}
      />

      {/* Body: sidebar + main */}
      <div className="flex flex-1 overflow-hidden">
        <QueueFilterPanel filters={filters} onChange={setFilters} open={filtersOpen} />

        <div className="flex-1 overflow-auto">
          {viewMode === "kanban" ? (
            <KanbanBoard
              encounters={encounters}
              isLoading={queueLoading}
              onStatusChange={handleStatusChange}
              onView={handleView}
              onMoveNext={handleMoveNext}
            />
          ) : (
            <QueueTable
              encounters={encounters}
              isLoading={queueLoading}
              onView={handleView}
              onMoveNext={handleMoveNext}
            />
          )}
        </div>
      </div>
    </div>
  );
}
