"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import type { TodaySummary } from "@/types/encounter-queue";
import { STATUS_COLOR, STATUS_LABEL } from "@/types/encounter-queue";
import { Download, Filter, LayoutGrid, List, Search } from "lucide-react";
import { Button } from "@/components/ui/button";

type Props = {
  summary: TodaySummary | undefined;
  isLoading: boolean;
  search: string;
  onSearchChange: (value: string) => void;
  viewMode: "kanban" | "table";
  onViewModeChange: (mode: "kanban" | "table") => void;
  onExport: () => void;
  onToggleFilters?: () => void;
  filtersOpen?: boolean;
};

export function QueueStatsBar({
  summary,
  isLoading,
  search,
  onSearchChange,
  viewMode,
  onViewModeChange,
  onExport,
  onToggleFilters,
  filtersOpen,
}: Props) {
  const [today, setToday] = useState("Today");

  useEffect(() => {
    // Run formatting client-side to avoid SSR/client locale differences.
    setToday(
      new Intl.DateTimeFormat("en-US", {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
      }).format(new Date())
    );
  }, []);

  return (
    <div className="sticky top-0 z-30 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex flex-wrap items-center gap-4 px-4 py-3">
        {/* Date + total */}
        <div className="mr-auto">
          <p className="text-sm text-muted-foreground" suppressHydrationWarning>
            {today}
          </p>
          <p className="text-lg font-semibold">
            Encounter Queue
            {summary ? (
              <span className="ml-2 text-base font-normal text-muted-foreground">
                {summary.total} total
              </span>
            ) : null}
          </p>
        </div>

        {/* Status badges */}
        <div className="hidden flex-wrap items-center gap-1.5 sm:flex">
          {isLoading
            ? Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-6 w-20 rounded-full" />
              ))
            : summary
              ? Object.entries(summary.by_status).map(([status, count]) =>
                  count > 0 ? (
                    <Badge
                      key={status}
                      variant="outline"
                      className={`${STATUS_COLOR[status] ?? ""} text-xs`}
                    >
                      {STATUS_LABEL[status] ?? status} {count}
                    </Badge>
                  ) : null
                )
              : null}
        </div>

        {/* Filters toggle (visible below lg) */}
        {onToggleFilters && (
          <Button
            size="sm"
            variant={filtersOpen ? "default" : "outline"}
            className="h-9 lg:hidden"
            onClick={onToggleFilters}
          >
            <Filter className="mr-1.5 h-4 w-4" />
            Filters
          </Button>
        )}

        {/* Search */}
        <div className="relative w-full sm:w-64">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search patients…"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-9 h-9"
          />
        </div>

        {/* View toggle */}
        <div className="flex rounded-md border">
          <Button
            size="sm"
            variant={viewMode === "kanban" ? "default" : "ghost"}
            className="rounded-r-none h-9 px-3"
            onClick={() => onViewModeChange("kanban")}
          >
            <LayoutGrid className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant={viewMode === "table" ? "default" : "ghost"}
            className="rounded-l-none h-9 px-3"
            onClick={() => onViewModeChange("table")}
          >
            <List className="h-4 w-4" />
          </Button>
        </div>

        {/* Export */}
        <Button size="sm" variant="outline" className="h-9" onClick={onExport}>
          <Download className="mr-1.5 h-4 w-4" />
          CSV
        </Button>
      </div>
    </div>
  );
}
