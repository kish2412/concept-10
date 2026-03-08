"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import {
  ENCOUNTER_STATUSES,
  ENCOUNTER_TYPES,
  STATUS_LABEL,
  TYPE_LABEL,
} from "@/types/encounter-queue";
import type { QueueFilters } from "@/types/encounter-queue";
import { RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";

type Props = {
  filters: QueueFilters;
  onChange: (filters: QueueFilters) => void;
  open?: boolean;
};

const EMPTY = "__all__";

export function QueueFilterPanel({ filters, onChange, open }: Props) {
  function set<K extends keyof QueueFilters>(key: K, value: string) {
    onChange({ ...filters, [key]: value === EMPTY ? "" : value });
  }

  function reset() {
    onChange({
      search: filters.search, // keep search
      status: "",
      encounter_type: "",
      provider_id: "",
      department_id: "",
    });
  }

  const hasFilters =
    filters.status || filters.encounter_type || filters.provider_id || filters.department_id;

  return (
    <aside
      className={cn(
        "w-56 shrink-0 space-y-5 border-r p-4 transition-all",
        "max-lg:absolute max-lg:inset-y-0 max-lg:left-0 max-lg:z-40 max-lg:bg-background max-lg:shadow-lg",
        !open && "max-lg:hidden"
      )}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Filters</h3>
        {hasFilters ? (
          <Button size="sm" variant="ghost" className="h-7 px-2 text-xs" onClick={reset}>
            <RotateCcw className="mr-1 h-3 w-3" />
            Reset
          </Button>
        ) : null}
      </div>

      {/* Status */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-muted-foreground">Status</label>
        <Select value={filters.status || EMPTY} onValueChange={(v) => set("status", v)}>
          <SelectTrigger className="h-8 text-xs">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={EMPTY}>All statuses</SelectItem>
            {ENCOUNTER_STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {STATUS_LABEL[s]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Type */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-muted-foreground">Type</label>
        <Select value={filters.encounter_type || EMPTY} onValueChange={(v) => set("encounter_type", v)}>
          <SelectTrigger className="h-8 text-xs">
            <SelectValue placeholder="All types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={EMPTY}>All types</SelectItem>
            {ENCOUNTER_TYPES.map((t) => (
              <SelectItem key={t} value={t}>
                {TYPE_LABEL[t]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Provider — placeholder until a providers list API exists */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-muted-foreground">Provider</label>
        <Select value={filters.provider_id || EMPTY} onValueChange={(v) => set("provider_id", v)}>
          <SelectTrigger className="h-8 text-xs">
            <SelectValue placeholder="All providers" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={EMPTY}>All providers</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Department — placeholder */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-muted-foreground">Department</label>
        <Select value={filters.department_id || EMPTY} onValueChange={(v) => set("department_id", v)}>
          <SelectTrigger className="h-8 text-xs">
            <SelectValue placeholder="All departments" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={EMPTY}>All departments</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </aside>
  );
}
