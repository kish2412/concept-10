"use client";

import { useCallback, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
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
  useAddMedication,
  useDebouncedValue,
  useDrugSearch,
  useRemoveMedication,
} from "@/lib/use-encounter-detail";
import {
  MEDICATION_FREQUENCIES,
  MEDICATION_ROUTES,
} from "@/types/encounter-detail";
import type { Encounter } from "@/types/encounter-queue";
import type { DrugSearchResult } from "@/types/encounter-detail";
import {
  AlertTriangle,
  Pill,
  Plus,
  Printer,
  Search,
  Send,
  Shield,
  Trash2,
  X,
} from "lucide-react";

type Props = {
  encounter: Encounter;
  readOnly: boolean;
};

export function PrescriptionsTab({ encounter, readOnly }: Props) {
  const [showForm, setShowForm] = useState(false);
  const [drugSearch, setDrugSearch] = useState("");
  const debouncedDrugSearch = useDebouncedValue(drugSearch, 300);
  const { data: drugResults, isLoading: searching } = useDrugSearch(debouncedDrugSearch);

  // Form state
  const [selectedDrug, setSelectedDrug] = useState<DrugSearchResult | null>(null);
  const [drugName, setDrugName] = useState("");
  const [genericName, setGenericName] = useState("");
  const [dosage, setDosage] = useState("");
  const [dosageUnit, setDosageUnit] = useState("mg");
  const [frequency, setFrequency] = useState("Once daily");
  const [route, setRoute] = useState("Oral");
  const [durationDays, setDurationDays] = useState("");
  const [quantity, setQuantity] = useState("");
  const [instructions, setInstructions] = useState("");
  const [isControlled, setIsControlled] = useState(false);

  // Interaction warnings
  const [interactions, setInteractions] = useState<string[]>([]);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [lastSentId, setLastSentId] = useState<string | null>(null);

  const addMedication = useAddMedication(encounter.id);
  const removeMedication = useRemoveMedication(encounter.id);

  const resetForm = () => {
    setSelectedDrug(null);
    setDrugName("");
    setGenericName("");
    setDosage("");
    setDosageUnit("mg");
    setFrequency("Once daily");
    setRoute("Oral");
    setDurationDays("");
    setQuantity("");
    setInstructions("");
    setIsControlled(false);
    setInteractions([]);
    setDrugSearch("");
  };

  const handleSelectDrug = (drug: DrugSearchResult) => {
    setSelectedDrug(drug);
    setDrugName(drug.name);
    setGenericName(drug.generic_name);
    setIsControlled(drug.is_controlled);
    setDrugSearch("");
    // Check interactions against current medications
    if (drug.interactions.length > 0) {
      const currentDrugNames = encounter.medications.map((m) =>
        m.drug_name.toLowerCase()
      );
      const found = drug.interactions.filter((interaction) =>
        currentDrugNames.some((name) => interaction.toLowerCase().includes(name))
      );
      setInteractions(found);
    }
  };

  const handleSubmit = useCallback(() => {
    if (!drugName.trim() || !dosage.trim()) return;
    addMedication.mutate(
      {
        drug_name: drugName,
        generic_name: genericName || undefined,
        drug_code: selectedDrug?.code,
        dosage,
        dosage_unit: dosageUnit,
        frequency,
        route,
        duration_days: durationDays ? parseInt(durationDays, 10) : undefined,
        quantity: quantity ? parseInt(quantity, 10) : undefined,
        special_instructions: instructions || undefined,
        is_controlled_substance: isControlled,
      },
      {
        onSuccess: () => {
          resetForm();
          setShowForm(false);
        },
      }
    );
  }, [
    addMedication,
    drugName,
    genericName,
    selectedDrug,
    dosage,
    dosageUnit,
    frequency,
    route,
    durationDays,
    quantity,
    instructions,
    isControlled,
  ]);

  const handleDelete = useCallback(() => {
    if (!deleteTarget) return;
    removeMedication.mutate(deleteTarget, {
      onSuccess: () => setDeleteTarget(null),
    });
  }, [deleteTarget, removeMedication]);

  const handlePrint = (medicationId: string) => {
    setLastSentId(null);
    window.print();
  };

  const handleSend = async (medicationId: string, line: string) => {
    try {
      await navigator.clipboard.writeText(line);
      setLastSentId(medicationId);
    } catch {
      setLastSentId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Interaction warning banner */}
      {interactions.length > 0 && (
        <div className="rounded-lg border border-red-300 bg-red-50 p-3 flex items-start gap-2">
          <AlertTriangle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-red-800">Drug Interaction Warning</p>
            <ul className="text-xs text-red-700 mt-1 list-disc list-inside">
              {interactions.map((i, idx) => (
                <li key={idx}>{i}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Add prescription */}
      {!readOnly && (
        <div>
          {!showForm ? (
            <Button size="sm" onClick={() => setShowForm(true)}>
              <Plus className="h-3.5 w-3.5 mr-1" />
              New Prescription
            </Button>
          ) : (
            <div className="rounded-lg border p-4 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold">New Prescription</h4>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    resetForm();
                    setShowForm(false);
                  }}
                >
                  Cancel
                </Button>
              </div>

              {/* Drug search */}
              {!selectedDrug && (
                <div className="space-y-2">
                  <Label className="text-xs">Search Drug</Label>
                  <div className="relative">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      value={drugSearch}
                      onChange={(e) => setDrugSearch(e.target.value)}
                      placeholder="Search by drug name or generic name..."
                      className="pl-9"
                    />
                  </div>
                  {drugSearch.length >= 2 && (
                    <div className="rounded-lg border max-h-40 overflow-y-auto">
                      {searching ? (
                        <div className="p-3 text-sm text-muted-foreground">Searching...</div>
                      ) : drugResults && drugResults.length > 0 ? (
                        drugResults.map((drug) => (
                          <button
                            key={drug.code}
                            className="flex items-center gap-2 w-full p-2.5 text-left text-sm hover:bg-muted/50 border-b last:border-0"
                            onClick={() => handleSelectDrug(drug)}
                          >
                            <div className="flex-1 min-w-0">
                              <p className="font-medium truncate">{drug.name}</p>
                              <p className="text-xs text-muted-foreground truncate">
                                {drug.generic_name}
                              </p>
                            </div>
                            {drug.is_controlled && (
                              <Badge variant="outline" className="text-[10px] bg-amber-50 text-amber-700 shrink-0">
                                <Shield className="h-3 w-3 mr-0.5" />
                                Controlled
                              </Badge>
                            )}
                          </button>
                        ))
                      ) : (
                        <div className="p-3 text-sm text-muted-foreground">No drugs found</div>
                      )}
                    </div>
                  )}
                  <p className="text-xs text-muted-foreground">
                    Or enter manually:
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1">
                      <Label className="text-xs">Drug Name</Label>
                      <Input
                        value={drugName}
                        onChange={(e) => setDrugName(e.target.value)}
                        placeholder="Brand name"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Generic Name</Label>
                      <Input
                        value={genericName}
                        onChange={(e) => setGenericName(e.target.value)}
                        placeholder="Generic name"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Selected drug display */}
              {selectedDrug && (
                <div className="flex items-center gap-2 rounded-md border bg-muted/30 px-3 py-2">
                  <Pill className="h-4 w-4 text-muted-foreground" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{selectedDrug.name}</p>
                    <p className="text-xs text-muted-foreground">{selectedDrug.generic_name}</p>
                  </div>
                  {selectedDrug.is_controlled && (
                    <Badge variant="outline" className="text-[10px] bg-amber-50 text-amber-700">
                      <Shield className="h-3 w-3 mr-0.5" />
                      Controlled
                    </Badge>
                  )}
                  <button onClick={resetForm}>
                    <X className="h-4 w-4 text-muted-foreground" />
                  </button>
                </div>
              )}

              {/* Prescription details */}
              {(selectedDrug || drugName) && (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="space-y-1">
                      <Label className="text-xs">Dosage</Label>
                      <Input
                        value={dosage}
                        onChange={(e) => setDosage(e.target.value)}
                        placeholder="e.g., 500"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Unit</Label>
                      <Select value={dosageUnit} onValueChange={setDosageUnit}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {["mg", "mcg", "g", "mL", "units", "puffs", "drops"].map((u) => (
                            <SelectItem key={u} value={u}>
                              {u}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Route</Label>
                      <Select value={route} onValueChange={setRoute}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {MEDICATION_ROUTES.map((r) => (
                            <SelectItem key={r} value={r}>
                              {r}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Frequency</Label>
                      <Select value={frequency} onValueChange={setFrequency}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {MEDICATION_FREQUENCIES.map((f) => (
                            <SelectItem key={f} value={f}>
                              {f}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label className="text-xs">Duration (days)</Label>
                      <Input
                        type="number"
                        value={durationDays}
                        onChange={(e) => setDurationDays(e.target.value)}
                        placeholder="e.g., 7"
                        min={1}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Quantity</Label>
                      <Input
                        type="number"
                        value={quantity}
                        onChange={(e) => setQuantity(e.target.value)}
                        placeholder="e.g., 30"
                        min={1}
                      />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Special Instructions</Label>
                    <Textarea
                      value={instructions}
                      onChange={(e) => setInstructions(e.target.value)}
                      placeholder="e.g., Take with food, Avoid alcohol..."
                      className="min-h-[60px]"
                    />
                  </div>
                  <div className="flex justify-end">
                    <Button
                      onClick={handleSubmit}
                      disabled={!drugName.trim() || !dosage.trim() || addMedication.isPending}
                    >
                      {addMedication.isPending ? "Prescribing..." : "Add Prescription"}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Prescriptions list */}
      {encounter.medications.length === 0 ? (
        <div className="text-center py-8 text-sm text-muted-foreground">
          <Pill className="h-8 w-8 mx-auto mb-2 opacity-50" />
          No prescriptions yet
        </div>
      ) : (
        <div className="space-y-2">
          {encounter.medications.map((med) => (
            <div
              key={med.id}
              className="rounded-md border px-4 py-3 space-y-1.5"
            >
              <div className="flex items-start gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold">{med.drug_name}</span>
                    {med.generic_name && (
                      <span className="text-xs text-muted-foreground">
                        ({med.generic_name})
                      </span>
                    )}
                    {med.is_controlled_substance && (
                      <Badge variant="outline" className="text-[10px] bg-amber-50 text-amber-700">
                        <Shield className="h-3 w-3 mr-0.5" />
                        Controlled
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {med.dosage} {med.dosage_unit} &middot; {med.route} &middot; {med.frequency}
                    {med.duration_days ? ` &middot; ${med.duration_days} days` : ""}
                    {med.quantity ? ` &middot; Qty: ${med.quantity}` : ""}
                  </p>
                  {med.special_instructions && (
                    <p className="text-xs text-muted-foreground mt-1 italic">
                      {med.special_instructions}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <Button
                    variant="ghost"
                    size="sm"
                    title="Print prescription"
                    onClick={() => handlePrint(med.id)}
                  >
                    <Printer className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    title="Send prescription"
                    onClick={() =>
                      handleSend(
                        med.id,
                        `${med.drug_name} ${med.dosage}${med.dosage_unit} ${med.route} ${med.frequency}`
                      )
                    }
                  >
                    <Send className="h-3.5 w-3.5" />
                  </Button>
                  {!readOnly && (
                    <button
                      onClick={() => setDeleteTarget(med.id)}
                      className="text-muted-foreground hover:text-red-600 p-1"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </div>
              <div className="text-xs text-muted-foreground">
                Prescribed{" "}
                {med.prescribed_at
                  ? new Date(med.prescribed_at).toLocaleString()
                  : new Date(med.created_at).toLocaleString()}
              </div>
              {lastSentId === med.id && (
                <div className="text-xs text-green-700">Prescription copied for sending.</div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Delete confirmation */}
      <Dialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove Prescription</DialogTitle>
            <DialogDescription>
              Are you sure you want to remove this prescription?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button
              onClick={handleDelete}
              disabled={removeMedication.isPending}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              {removeMedication.isPending ? "Removing..." : "Remove"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
