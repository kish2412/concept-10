"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { QueueStatsBar } from "@/components/encounters/queue-stats-bar";
import { QueueFilterPanel } from "@/components/encounters/queue-filter-panel";
import { KanbanBoard } from "@/components/encounters/kanban-board";
import { QueueTable } from "@/components/encounters/queue-table";
import { TriageHandoffDialog } from "@/components/encounters/triage-handoff-dialog";
import {
  useEncounterQueue,
  useTodaySummary,
  useUpdateEncounterStatus,
  useExportQueueCsv,
} from "@/lib/use-encounter-queue";
import type {
  Encounter,
  EncounterStatus,
  QueueFilters,
  TriageAssessment,
} from "@/types/encounter-queue";
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
  const [triageDialogEncounter, setTriageDialogEncounter] = useState<Encounter | null>(null);
  const [pendingStatus, setPendingStatus] = useState<EncounterStatus | null>(null);

  // ── Data ──
  const { data: queueData, isLoading: queueLoading } = useEncounterQueue(filters);
  const { data: summary, isLoading: summaryLoading } = useTodaySummary();
  const statusMutation = useUpdateEncounterStatus();
  const exportCsv = useExportQueueCsv();

  const encounters = useMemo(() => queueData?.items ?? [], [queueData?.items]);

  function startStatusTransition(encounter: Encounter, nextStatus: EncounterStatus) {
    if (nextStatus === "WITH_PROVIDER") {
      setTriageDialogEncounter(encounter);
      setPendingStatus(nextStatus);
      return;
    }
    statusMutation.mutate({ id: encounter.id, status: nextStatus });
  }

  function closeTriageDialog() {
    setTriageDialogEncounter(null);
    setPendingStatus(null);
  }

  function submitTriageAndMove(triageAssessment: TriageAssessment) {
    if (!triageDialogEncounter || !pendingStatus) {
      return;
    }
    statusMutation.mutate(
      {
        id: triageDialogEncounter.id,
        status: pendingStatus,
        triageAssessment,
      },
      {
        onSuccess: () => {
          closeTriageDialog();
        },
      }
    );
  }

  // ── Handlers ──
  function handleView(enc: Encounter) {
    router.push(`/encounters/${enc.id}`);
  }

  function handleMoveNext(enc: Encounter) {
    const next = NEXT_STATUS[enc.status as EncounterStatus];
    if (next) {
      startStatusTransition(enc, next);
    }
  }

  function handleStatusChange(encId: string, newStatus: EncounterStatus) {
    const encounter = encounters.find((item) => item.id === encId);
    if (!encounter) {
      return;
    }
    startStatusTransition(encounter, newStatus);
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
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-lg border bg-background">
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
      <div className="relative flex min-h-0 flex-1 overflow-hidden">
        <QueueFilterPanel filters={filters} onChange={setFilters} open={filtersOpen} />

        <div className="min-h-0 flex-1 overflow-auto">
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

      <TriageHandoffDialog
        open={Boolean(triageDialogEncounter && pendingStatus === "WITH_PROVIDER")}
        encounter={triageDialogEncounter}
        isSubmitting={statusMutation.isPending}
        onCancel={closeTriageDialog}
        onSubmit={submitTriageAndMove}
      />
    </div>
  );
}
