"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  useEncounterDetailPage,
  usePatientProfile,
  useUnsavedChanges,
} from "@/lib/use-encounter-detail";
import {
  STATUS_COLOR,
  STATUS_LABEL,
  TYPE_LABEL,
} from "@/types/encounter-queue";
import { OverviewTab } from "@/components/encounters/detail/overview-tab";
import { ClinicalNotesTab } from "@/components/encounters/detail/clinical-notes-tab";
import { DiagnosesTab } from "@/components/encounters/detail/diagnoses-tab";
import { OrdersTab } from "@/components/encounters/detail/orders-tab";
import { PrescriptionsTab } from "@/components/encounters/detail/prescriptions-tab";
import { DispositionTab } from "@/components/encounters/detail/disposition-tab";
import { EncounterTimeline } from "@/components/encounters/detail/encounter-timeline";
import { EncounterSinglePageView } from "@/components/encounters/detail/single-page-view";
import {
  Activity,
  ArrowLeft,
  ClipboardList,
  FileText,
  Keyboard,
  LogOut,
  Pill,
  Search,
  Stethoscope,
} from "lucide-react";

export default function EncounterDetailPage() {
  const params = useParams();
  const router = useRouter();
  const encounterId = params.id as string;

  const { data: encounter, isLoading, error } = useEncounterDetailPage(encounterId);
  const { data: patientProfile } = usePatientProfile(encounter?.patient_id ?? null);

  const [activeTab, setActiveTab] = useState("overview");
  const [detailView, setDetailView] = useState<"tabular" | "single">("tabular");
  const [hasDirtyNotes, setHasDirtyNotes] = useState(false);
  const [hasDirtyDisposition, setHasDirtyDisposition] = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const hasUnsavedChanges = hasDirtyNotes || hasDirtyDisposition;

  const isReadOnly = encounter?.status === "DISCHARGED";

  // Unsaved changes warning on page leave
  useUnsavedChanges(hasUnsavedChanges);

  // Tab change with unsaved warning
  const handleTabChange = useCallback(
    (tab: string) => {
      if (hasUnsavedChanges) {
        const confirmed = window.confirm(
          "You have unsaved changes. Switch tabs anyway?"
        );
        if (!confirmed) return;
      }
      setActiveTab(tab);
    },
    [hasUnsavedChanges]
  );

  // Keyboard shortcut: Ctrl+K to show shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setShowShortcuts((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-6 w-1/4" />
        <div className="grid grid-cols-[1fr_240px] gap-6">
          <div className="space-y-4">
            <Skeleton className="h-40 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
          <Skeleton className="h-[400px]" />
        </div>
      </div>
    );
  }

  if (error || !encounter) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
        <div className="text-center py-12">
          <p className="text-lg font-semibold text-muted-foreground">
            Encounter not found
          </p>
          <p className="text-sm text-muted-foreground mt-1">
            The encounter may have been deleted or you don&apos;t have access.
          </p>
        </div>
      </div>
    );
  }

  const patientName = encounter.patient
    ? `${encounter.patient.first_name} ${encounter.patient.last_name}`
    : "Unknown Patient";

  return (
    <TooltipProvider>
      <div className="space-y-4">
        {/* Page header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => router.back()}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold">{patientName}</h1>
                <Badge
                  variant="outline"
                  className={`text-xs ${STATUS_COLOR[encounter.status] ?? ""}`}
                >
                  {STATUS_LABEL[encounter.status] ?? encounter.status}
                </Badge>
                {isReadOnly && (
                  <Badge variant="outline" className="text-xs bg-gray-100 text-gray-600">
                    Read-only
                  </Badge>
                )}
              </div>
              <p className="text-sm text-muted-foreground">
                {encounter.encounter_id} &middot;{" "}
                {TYPE_LABEL[encounter.encounter_type] ?? encounter.encounter_type} &middot;{" "}
                {new Date(encounter.scheduled_at || encounter.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="inline-flex rounded-md border bg-background p-1">
              <Button
                variant={detailView === "tabular" ? "default" : "ghost"}
                size="sm"
                onClick={() => setDetailView("tabular")}
              >
                Tabular
              </Button>
              <Button
                variant={detailView === "single" ? "default" : "ghost"}
                size="sm"
                onClick={() => setDetailView("single")}
              >
                Single Page
              </Button>
            </div>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowShortcuts(!showShortcuts)}
                >
                  <Keyboard className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Keyboard shortcuts (Ctrl+K)</p>
              </TooltipContent>
            </Tooltip>
          </div>
        </div>

        {/* Keyboard shortcuts panel */}
        {showShortcuts && (
          <div className="rounded-lg border bg-muted/30 p-3 text-xs space-y-1">
            <p className="font-semibold mb-1">Keyboard Shortcuts</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              <span>
                <kbd className="rounded border px-1 py-0.5 font-mono text-[10px]">Ctrl+S</kbd>{" "}
                Save note
              </span>
              <span>
                <kbd className="rounded border px-1 py-0.5 font-mono text-[10px]">Ctrl+K</kbd>{" "}
                Toggle shortcuts
              </span>
            </div>
          </div>
        )}

        {/* Main content + timeline sidebar */}
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_240px] gap-6">
          {detailView === "tabular" ? (
            <Tabs value={activeTab} onValueChange={handleTabChange}>
              <TabsList className="w-full justify-start overflow-x-auto whitespace-nowrap">
                <TabsTrigger value="overview" className="gap-1">
                  <Activity className="h-3.5 w-3.5" />
                  Overview
                </TabsTrigger>
                <TabsTrigger value="notes" className="gap-1">
                  <FileText className="h-3.5 w-3.5" />
                  Clinical Notes
                  {hasDirtyNotes && (
                    <span className="ml-1 h-1.5 w-1.5 rounded-full bg-yellow-500" />
                  )}
                </TabsTrigger>
                <TabsTrigger value="diagnoses" className="gap-1">
                  <Search className="h-3.5 w-3.5" />
                  Diagnoses
                  {encounter.diagnoses.length > 0 && (
                    <Badge variant="secondary" className="ml-1 h-4 min-w-[16px] px-1 text-[10px]">
                      {encounter.diagnoses.length}
                    </Badge>
                  )}
                </TabsTrigger>
                <TabsTrigger value="orders" className="gap-1">
                  <ClipboardList className="h-3.5 w-3.5" />
                  Orders
                  {encounter.orders.length > 0 && (
                    <Badge variant="secondary" className="ml-1 h-4 min-w-[16px] px-1 text-[10px]">
                      {encounter.orders.length}
                    </Badge>
                  )}
                </TabsTrigger>
                <TabsTrigger value="prescriptions" className="gap-1">
                  <Pill className="h-3.5 w-3.5" />
                  Medications
                  {encounter.medications.length > 0 && (
                    <Badge variant="secondary" className="ml-1 h-4 min-w-[16px] px-1 text-[10px]">
                      {encounter.medications.length}
                    </Badge>
                  )}
                </TabsTrigger>
                <TabsTrigger value="disposition" className="gap-1">
                  <LogOut className="h-3.5 w-3.5" />
                  Disposition
                </TabsTrigger>
              </TabsList>

              <p className="mt-2 text-xs text-muted-foreground">
                If you do not see all tabs, scroll horizontally in the tab bar.
              </p>

              <TabsContent value="overview">
                <OverviewTab
                  encounter={encounter}
                  patientProfile={patientProfile?.patient}
                  patientBackground={patientProfile?.background}
                />
              </TabsContent>

              <TabsContent value="notes">
                <ClinicalNotesTab
                  encounter={encounter}
                  readOnly={isReadOnly}
                  onDirtyChange={setHasDirtyNotes}
                />
              </TabsContent>

              <TabsContent value="diagnoses">
                <DiagnosesTab encounter={encounter} readOnly={isReadOnly} />
              </TabsContent>

              <TabsContent value="orders">
                <OrdersTab encounter={encounter} readOnly={isReadOnly} />
              </TabsContent>

              <TabsContent value="prescriptions">
                <PrescriptionsTab encounter={encounter} readOnly={isReadOnly} />
              </TabsContent>

              <TabsContent value="disposition">
                <DispositionTab
                  encounter={encounter}
                  readOnly={isReadOnly}
                  onDirtyChange={setHasDirtyDisposition}
                />
              </TabsContent>
            </Tabs>
          ) : (
            <EncounterSinglePageView
              encounter={encounter}
              patientProfile={patientProfile?.patient}
              patientBackground={patientProfile?.background}
              readOnly={isReadOnly}
              onDirtyNotesChange={setHasDirtyNotes}
              onDirtyDispositionChange={setHasDirtyDisposition}
            />
          )}

          {/* Timeline sidebar */}
          <aside className="hidden xl:block border-l pl-4">
            <EncounterTimeline encounter={encounter} />
          </aside>
        </div>
      </div>
    </TooltipProvider>
  );
}
