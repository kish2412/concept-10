"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RichTextEditor } from "@/components/ui/rich-text-editor";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  useCompleteEncounter,
  useSaveDisposition,
} from "@/lib/use-encounter-detail";
import {
  DISPOSITION_LABELS,
  DISPOSITION_TYPES,
} from "@/types/encounter-detail";
import type { Encounter } from "@/types/encounter-queue";
import {
  AlertCircle,
  Calendar,
  CheckCircle,
  FileText,
  LogOut,
} from "lucide-react";

type Props = {
  encounter: Encounter;
  readOnly: boolean;
  onDirtyChange: (dirty: boolean) => void;
};

export function DispositionTab({ encounter, readOnly, onDirtyChange }: Props) {
  const existing = encounter.disposition;
  const [dispositionId, setDispositionId] = useState<string | null>(
    existing?.id ?? null
  );

  const [dispositionType, setDispositionType] = useState<string>(
    existing?.disposition_type ?? "DISCHARGE"
  );
  const [followUpRequired, setFollowUpRequired] = useState(
    existing?.follow_up_required ?? false
  );
  const [followUpDays, setFollowUpDays] = useState(
    existing?.follow_up_in_days?.toString() ?? ""
  );
  const [followUpDate, setFollowUpDate] = useState("");
  const [dischargeInstructions, setDischargeInstructions] = useState(
    existing?.discharge_instructions ?? ""
  );
  const [activityRestrictions, setActivityRestrictions] = useState(
    existing?.activity_restrictions ?? ""
  );
  const [dietInstructions, setDietInstructions] = useState(
    existing?.diet_instructions ?? ""
  );
  const [educationMaterials, setEducationMaterials] = useState<string[]>(
    Array.isArray(existing?.patient_education_materials)
      ? (existing?.patient_education_materials as string[])
      : []
  );
  const [showCompleteModal, setShowCompleteModal] = useState(false);

  const saveDisposition = useSaveDisposition(encounter.id);
  const completeEncounter = useCompleteEncounter(encounter.id);

  useEffect(() => {
    if (existing?.id) setDispositionId(existing.id);
  }, [existing?.id]);

  const baseSnapshot = useMemo(
    () =>
      JSON.stringify({
        dispositionType: existing?.disposition_type ?? "DISCHARGE",
        followUpRequired: existing?.follow_up_required ?? false,
        followUpDays: existing?.follow_up_in_days?.toString() ?? "",
        dischargeInstructions: existing?.discharge_instructions ?? "",
        activityRestrictions: existing?.activity_restrictions ?? "",
        dietInstructions: existing?.diet_instructions ?? "",
        educationMaterials: Array.isArray(existing?.patient_education_materials)
          ? (existing?.patient_education_materials as string[])
          : [],
      }),
    [existing]
  );

  const currentSnapshot = useMemo(
    () =>
      JSON.stringify({
        dispositionType,
        followUpRequired,
        followUpDays,
        dischargeInstructions,
        activityRestrictions,
        dietInstructions,
        educationMaterials,
      }),
    [
      dispositionType,
      followUpRequired,
      followUpDays,
      dischargeInstructions,
      activityRestrictions,
      dietInstructions,
      educationMaterials,
    ]
  );

  const isDirty = currentSnapshot !== baseSnapshot;

  useEffect(() => {
    onDirtyChange(!readOnly && isDirty);
  }, [isDirty, onDirtyChange, readOnly]);

  const handleSave = useCallback(() => {
    saveDisposition.mutate({
      disposition_id: dispositionId ?? undefined,
      disposition_type: dispositionType,
      follow_up_required: followUpRequired,
      follow_up_in_days: followUpDays ? parseInt(followUpDays, 10) : undefined,
      discharge_instructions: dischargeInstructions || undefined,
      activity_restrictions: activityRestrictions || undefined,
      diet_instructions: dietInstructions || undefined,
      patient_education_materials:
        educationMaterials.length > 0 ? educationMaterials : undefined,
    }, {
      onSuccess: (saved) => {
        if (saved?.id) setDispositionId(saved.id);
      },
    });
  }, [
    saveDisposition,
    dispositionId,
    dispositionType,
    followUpRequired,
    followUpDays,
    dischargeInstructions,
    activityRestrictions,
    dietInstructions,
    educationMaterials,
  ]);

  // Validation checks before completing encounter
  const validationErrors: string[] = [];
  if (encounter.diagnoses.length === 0) validationErrors.push("At least one diagnosis is required");
  if (!encounter.notes.some((n) => n.is_signed)) validationErrors.push("A signed clinical note is required");
  if (!dispositionType) validationErrors.push("Disposition type must be selected");

  const handleComplete = useCallback(async () => {
    try {
      await saveDisposition.mutateAsync({
        disposition_id: dispositionId ?? undefined,
        disposition_type: dispositionType,
        follow_up_required: followUpRequired,
        follow_up_in_days: followUpDays ? parseInt(followUpDays, 10) : undefined,
        discharge_instructions: dischargeInstructions || undefined,
        activity_restrictions: activityRestrictions || undefined,
        diet_instructions: dietInstructions || undefined,
        patient_education_materials:
          educationMaterials.length > 0 ? educationMaterials : undefined,
      });

      completeEncounter.mutate(undefined, {
        onSuccess: () => setShowCompleteModal(false),
      });
    } catch {
      // Keep modal open if save fails.
    }
  }, [
    completeEncounter,
    dispositionId,
    dietInstructions,
    dischargeInstructions,
    dispositionType,
    educationMaterials,
    followUpDays,
    followUpRequired,
    saveDisposition,
    activityRestrictions,
  ]);

  // Calculate follow-up date from days
  const computedFollowUpDate = followUpDays
    ? new Date(Date.now() + parseInt(followUpDays, 10) * 86400000)
        .toISOString()
        .slice(0, 10)
    : "";

  // Available education materials (would come from API in production)
  const availableMaterials = [
    {
      id: "post-discharge-care-guide",
      title: "Post-Discharge Care Guide",
      url: "https://example.com/materials/post-discharge-care-guide.pdf",
    },
    {
      id: "medication-management",
      title: "Medication Management",
      url: "https://example.com/materials/medication-management.pdf",
    },
    {
      id: "return-to-er",
      title: "When to Return to the ER",
      url: "https://example.com/materials/when-to-return-to-er.pdf",
    },
    {
      id: "wound-care",
      title: "Wound Care Instructions",
      url: "https://example.com/materials/wound-care-instructions.pdf",
    },
    {
      id: "diet-activity-guidelines",
      title: "Diet and Activity Guidelines",
      url: "https://example.com/materials/diet-and-activity-guidelines.pdf",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Disposition type */}
      <div className="space-y-3">
        <Label className="text-xs font-semibold uppercase tracking-wide">
          Disposition Type
        </Label>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {DISPOSITION_TYPES.map((type) => (
            <button
              key={type}
              disabled={readOnly}
              onClick={() => setDispositionType(type)}
              className={`rounded-lg border p-3 text-sm text-left transition-colors ${
                dispositionType === type
                  ? "border-primary bg-primary/5 font-medium"
                  : "hover:bg-muted/50"
              } ${readOnly ? "opacity-60 cursor-not-allowed" : ""}`}
            >
              {DISPOSITION_LABELS[type]}
            </button>
          ))}
        </div>
      </div>

      {/* Follow-up scheduling */}
      <div className="space-y-3">
        <Label className="text-xs font-semibold uppercase tracking-wide">
          Follow-up
        </Label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={followUpRequired}
            onChange={(e) => setFollowUpRequired(e.target.checked)}
            disabled={readOnly}
            className="rounded border-input"
          />
          Follow-up required
        </label>
        {followUpRequired && (
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Follow-up in (days)</Label>
              <Input
                type="number"
                value={followUpDays}
                onChange={(e) => setFollowUpDays(e.target.value)}
                placeholder="e.g., 7"
                min={1}
                disabled={readOnly}
              />
              {computedFollowUpDate && (
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  ~{new Date(computedFollowUpDate).toLocaleDateString()}
                </p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Specific Date (optional)</Label>
              <Input
                type="date"
                value={followUpDate}
                onChange={(e) => setFollowUpDate(e.target.value)}
                disabled={readOnly}
              />
            </div>
          </div>
        )}
      </div>

      {/* Discharge instructions */}
      <div className="space-y-2">
        <Label className="text-xs font-semibold uppercase tracking-wide">
          Discharge Instructions
        </Label>
        <RichTextEditor
          value={dischargeInstructions}
          onChange={setDischargeInstructions}
          placeholder="Activity restrictions, wound care, warning signs to watch for..."
          className="min-h-[120px]"
          disabled={readOnly}
        />
      </div>

      {/* Activity restrictions */}
      <div className="space-y-2">
        <Label className="text-xs font-semibold uppercase tracking-wide">
          Activity Restrictions
        </Label>
        <RichTextEditor
          value={activityRestrictions}
          onChange={setActivityRestrictions}
          placeholder="e.g., No heavy lifting for 2 weeks..."
          className="min-h-[90px]"
          disabled={readOnly}
        />
      </div>

      {/* Diet instructions */}
      <div className="space-y-2">
        <Label className="text-xs font-semibold uppercase tracking-wide">
          Diet Instructions
        </Label>
        <RichTextEditor
          value={dietInstructions}
          onChange={setDietInstructions}
          placeholder="e.g., Clear liquids for 24 hours, then advance as tolerated..."
          className="min-h-[90px]"
          disabled={readOnly}
        />
      </div>

      {/* Patient education materials */}
      <div className="space-y-2">
        <Label className="text-xs font-semibold uppercase tracking-wide">
          Patient Education Materials
        </Label>
        <div className="space-y-1.5">
          {availableMaterials.map((mat) => (
            <label
              key={mat.id}
              className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-muted/30"
            >
              <input
                type="checkbox"
                checked={educationMaterials.includes(mat.id)}
                onChange={(e) => {
                  if (e.target.checked) {
                    setEducationMaterials((prev) => [...prev, mat.id]);
                  } else {
                    setEducationMaterials((prev) => prev.filter((id) => id !== mat.id));
                  }
                }}
                disabled={readOnly}
                className="rounded border-input"
              />
              <FileText className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="flex-1">{mat.title}</span>
              <a
                href={mat.url}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-primary underline"
                onClick={(e) => e.stopPropagation()}
              >
                PDF
              </a>
            </label>
          ))}
        </div>
      </div>

      {/* Action buttons */}
      {!readOnly && (
        <div className="flex items-center gap-3 border-t pt-4">
          <Button
            variant="outline"
            onClick={handleSave}
            disabled={saveDisposition.isPending}
          >
            {saveDisposition.isPending ? "Saving..." : "Save Disposition"}
          </Button>
          <Button
            onClick={() => setShowCompleteModal(true)}
            disabled={validationErrors.length > 0}
            className="bg-green-600 hover:bg-green-700 text-white"
          >
            <CheckCircle className="h-4 w-4 mr-1.5" />
            Complete Encounter
          </Button>
          {validationErrors.length > 0 && (
            <div className="flex items-start gap-1.5 text-xs text-amber-600">
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              <div>
                {validationErrors.map((err, i) => (
                  <p key={i}>{err}</p>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Already discharged indicator */}
      {encounter.status === "DISCHARGED" && (
        <div className="rounded-lg border bg-muted/30 p-4 flex items-center gap-2 text-sm text-muted-foreground">
          <LogOut className="h-4 w-4" />
          This encounter has been completed and discharged.
          {encounter.disposition?.discharged_at && (
            <span>
              Discharged at{" "}
              {new Date(encounter.disposition.discharged_at).toLocaleString()}
            </span>
          )}
        </div>
      )}

      {/* Complete encounter modal */}
      <Dialog open={showCompleteModal} onOpenChange={setShowCompleteModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Complete Encounter</DialogTitle>
            <DialogDescription>
              This will mark the encounter as DISCHARGED. The disposition and
              all clinical notes will be locked. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="text-sm space-y-1">
            <p>
              <strong>Disposition:</strong>{" "}
              {DISPOSITION_LABELS[dispositionType] ?? dispositionType}
            </p>
            {followUpRequired && (
              <p>
                <strong>Follow-up:</strong> {followUpDays} days
              </p>
            )}
            <p>
              <strong>Diagnoses:</strong> {encounter.diagnoses.length}
            </p>
            <p>
              <strong>Orders:</strong> {encounter.orders.length}
            </p>
            <p>
              <strong>Prescriptions:</strong> {encounter.medications.length}
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCompleteModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleComplete}
              disabled={completeEncounter.isPending}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              {completeEncounter.isPending ? "Completing..." : "Complete & Discharge"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
