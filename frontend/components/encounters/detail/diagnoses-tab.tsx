"use client";

import { useCallback, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  useAddDiagnosis,
  useDebouncedValue,
  useICD10Search,
  useRemoveDiagnosis,
} from "@/lib/use-encounter-detail";
import { DIAGNOSIS_TYPES } from "@/types/encounter-detail";
import type { Encounter } from "@/types/encounter-queue";
import { AlertCircle, Plus, Search, Trash2, X } from "lucide-react";

type Props = {
  encounter: Encounter;
  readOnly: boolean;
};

export function DiagnosesTab({ encounter, readOnly }: Props) {
  const [searchQuery, setSearchQuery] = useState("");
  const debouncedQuery = useDebouncedValue(searchQuery, 300);
  const { data: searchResults, isLoading: searching } = useICD10Search(debouncedQuery);

  const [selectedType, setSelectedType] = useState<string>("PRIMARY");
  const [isChronic, setIsChronic] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const addDiagnosis = useAddDiagnosis(encounter.id);
  const removeDiagnosis = useRemoveDiagnosis(encounter.id);

  const handleAdd = useCallback(
    (code: string, description: string) => {
      addDiagnosis.mutate(
        {
          icd_code: code,
          icd_description: description,
          diagnosis_type: selectedType,
          is_chronic_condition: isChronic,
        },
        {
          onSuccess: () => {
            setSearchQuery("");
            setIsChronic(false);
          },
        }
      );
    },
    [addDiagnosis, selectedType, isChronic]
  );

  const handleDelete = useCallback(() => {
    if (!deleteTarget) return;
    removeDiagnosis.mutate(deleteTarget, {
      onSuccess: () => setDeleteTarget(null),
    });
  }, [deleteTarget, removeDiagnosis]);

  // Group by type
  const grouped = {
    PRIMARY: encounter.diagnoses.filter((d) => d.diagnosis_type === "PRIMARY"),
    SECONDARY: encounter.diagnoses.filter((d) => d.diagnosis_type === "SECONDARY"),
    DIFFERENTIAL: encounter.diagnoses.filter((d) => d.diagnosis_type === "DIFFERENTIAL"),
    RULE_OUT: encounter.diagnoses.filter((d) => d.diagnosis_type === "RULE_OUT"),
  };

  return (
    <div className="space-y-6">
      {/* Search bar */}
      {!readOnly && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search ICD-10 codes (e.g., J06.9, upper respiratory...)"
                className="pl-9"
              />
              {searchQuery && (
                <button
                  className="absolute right-2.5 top-1/2 -translate-y-1/2"
                  onClick={() => setSearchQuery("")}
                >
                  <X className="h-4 w-4 text-muted-foreground" />
                </button>
              )}
            </div>
            <Select value={selectedType} onValueChange={setSelectedType}>
              <SelectTrigger className="w-[150px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DIAGNOSIS_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t.charAt(0) + t.slice(1).toLowerCase().replace("_", " ")}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <label className="flex items-center gap-1.5 text-sm whitespace-nowrap">
              <input
                type="checkbox"
                checked={isChronic}
                onChange={(e) => setIsChronic(e.target.checked)}
                className="rounded border-input"
              />
              Chronic
            </label>
          </div>

          {/* Search results dropdown */}
          {searchQuery.length >= 2 && (
            <div className="rounded-lg border max-h-48 overflow-y-auto">
              {searching ? (
                <div className="p-3 text-sm text-muted-foreground">Searching...</div>
              ) : searchResults && searchResults.length > 0 ? (
                searchResults.map((r) => (
                  <button
                    key={r.code}
                    className="flex items-center gap-2 w-full p-2.5 text-left text-sm hover:bg-muted/50 border-b last:border-0"
                    onClick={() => handleAdd(r.code, r.description)}
                  >
                    <Badge variant="outline" className="text-[10px] font-mono shrink-0">
                      {r.code}
                    </Badge>
                    <span className="truncate">{r.description}</span>
                    <Plus className="h-4 w-4 ml-auto shrink-0 text-muted-foreground" />
                  </button>
                ))
              ) : (
                <div className="p-3 text-sm text-muted-foreground">
                  No results found for &ldquo;{searchQuery}&rdquo;
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Diagnoses list */}
      {encounter.diagnoses.length === 0 ? (
        <div className="text-center py-8 text-sm text-muted-foreground">
          <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
          No diagnoses added yet
        </div>
      ) : (
        <div className="space-y-4">
          {(Object.entries(grouped) as [string, typeof encounter.diagnoses][]).map(
            ([type, items]) =>
              items.length > 0 && (
                <div key={type} className="space-y-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {type.charAt(0) + type.slice(1).toLowerCase().replace("_", " ")} ({items.length})
                  </h4>
                  <div className="space-y-1">
                    {items.map((dx) => (
                      <div
                        key={dx.id}
                        className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm"
                      >
                        <Badge variant="outline" className="text-[10px] font-mono shrink-0">
                          {dx.icd_code}
                        </Badge>
                        <span className="flex-1 truncate">{dx.icd_description}</span>
                        {dx.is_chronic_condition && (
                          <Badge variant="outline" className="text-[10px] bg-purple-50 text-purple-700">
                            Chronic
                          </Badge>
                        )}
                        {dx.onset_date && (
                          <span className="text-xs text-muted-foreground">
                            Onset: {new Date(dx.onset_date).toLocaleDateString()}
                          </span>
                        )}
                        {!readOnly && (
                          <button
                            onClick={() => setDeleteTarget(dx.id)}
                            className="text-muted-foreground hover:text-red-600 shrink-0"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )
          )}
        </div>
      )}

      {/* Delete confirmation modal */}
      <Dialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove Diagnosis</DialogTitle>
            <DialogDescription>
              Are you sure you want to remove this diagnosis from the encounter?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="default"
              onClick={handleDelete}
              disabled={removeDiagnosis.isPending}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              {removeDiagnosis.isPending ? "Removing..." : "Remove"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
