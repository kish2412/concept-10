"use client";

import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { Encounter, TriageAssessment } from "@/types/encounter-queue";

const ACUITY_OPTIONS: Array<TriageAssessment["acuity"]> = [
  "RESUSCITATION",
  "EMERGENT",
  "URGENT",
  "LESS_URGENT",
  "NON_URGENT",
];

type Props = {
  open: boolean;
  encounter: Encounter | null;
  isSubmitting: boolean;
  onCancel: () => void;
  onSubmit: (payload: TriageAssessment) => void;
};

export function TriageHandoffDialog({
  open,
  encounter,
  isSubmitting,
  onCancel,
  onSubmit,
}: Props) {
  const [acuity, setAcuity] = useState<TriageAssessment["acuity"]>("URGENT");
  const [presentingSymptoms, setPresentingSymptoms] = useState("");
  const [symptomOnset, setSymptomOnset] = useState("");
  const [painScore, setPainScore] = useState("");
  const [redFlags, setRedFlags] = useState("");
  const [isolationRequired, setIsolationRequired] = useState<"yes" | "no">("no");
  const [mobilityStatus, setMobilityStatus] = useState("");
  const [allergiesVerified, setAllergiesVerified] = useState<"yes" | "no">("no");
  const [triageNotes, setTriageNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    const existing = encounter?.triage_assessment;
    setAcuity(existing?.acuity ?? "URGENT");
    setPresentingSymptoms(existing?.presenting_symptoms?.join(", ") ?? "");
    setSymptomOnset(existing?.symptom_onset ?? "");
    setPainScore(existing?.pain_score != null ? String(existing.pain_score) : "");
    setRedFlags(existing?.red_flags?.join(", ") ?? "");
    setIsolationRequired(existing?.isolation_required ? "yes" : "no");
    setMobilityStatus(existing?.mobility_status ?? "");
    setAllergiesVerified(existing?.allergies_verified ? "yes" : "no");
    setTriageNotes(existing?.triage_notes ?? "");
    setError(null);
  }, [encounter, open]);

  const parsedSymptoms = useMemo(
    () => presentingSymptoms.split(",").map((item) => item.trim()).filter(Boolean),
    [presentingSymptoms]
  );

  function handleSave() {
    if (parsedSymptoms.length === 0) {
      setError("Add at least one presenting symptom.");
      return;
    }
    if (triageNotes.trim().length < 10) {
      setError("Triage notes must be at least 10 characters.");
      return;
    }

    const pain = painScore.trim();
    const painNumber = pain ? Number(pain) : null;
    if (painNumber != null && (Number.isNaN(painNumber) || painNumber < 0 || painNumber > 10)) {
      setError("Pain score must be between 0 and 10.");
      return;
    }

    setError(null);
    onSubmit({
      acuity,
      presenting_symptoms: parsedSymptoms,
      symptom_onset: symptomOnset.trim() || null,
      pain_score: painNumber,
      red_flags: redFlags.split(",").map((item) => item.trim()).filter(Boolean),
      isolation_required: isolationRequired === "yes",
      mobility_status: mobilityStatus.trim() || null,
      allergies_verified: allergiesVerified === "yes",
      triage_notes: triageNotes.trim(),
    });
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onCancel()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Triage Handoff Before In Consultation</DialogTitle>
          <DialogDescription>
            Complete detailed triage for this encounter before moving to in-consultation.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-1.5">
            <Label>Acuity</Label>
            <Select value={acuity} onValueChange={(value) => setAcuity(value as TriageAssessment["acuity"])}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ACUITY_OPTIONS.map((option) => (
                  <SelectItem key={option} value={option}>
                    {option.replaceAll("_", " ")}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>Symptom onset</Label>
            <Input
              placeholder="e.g. 6 hours ago"
              value={symptomOnset}
              onChange={(event) => setSymptomOnset(event.target.value)}
            />
          </div>

          <div className="space-y-1.5 md:col-span-2">
            <Label>Presenting symptoms (comma-separated)</Label>
            <Input
              placeholder="fever, dry cough, fatigue"
              value={presentingSymptoms}
              onChange={(event) => setPresentingSymptoms(event.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label>Pain score (0-10)</Label>
            <Input
              type="number"
              min={0}
              max={10}
              value={painScore}
              onChange={(event) => setPainScore(event.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label>Mobility status</Label>
            <Input
              placeholder="e.g. ambulatory"
              value={mobilityStatus}
              onChange={(event) => setMobilityStatus(event.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label>Isolation required?</Label>
            <Select value={isolationRequired} onValueChange={(value) => setIsolationRequired(value as "yes" | "no") }>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="no">No</SelectItem>
                <SelectItem value="yes">Yes</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>Allergies verified?</Label>
            <Select value={allergiesVerified} onValueChange={(value) => setAllergiesVerified(value as "yes" | "no") }>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="yes">Yes</SelectItem>
                <SelectItem value="no">No</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5 md:col-span-2">
            <Label>Red flags (comma-separated)</Label>
            <Input
              placeholder="hypotension, altered mental status"
              value={redFlags}
              onChange={(event) => setRedFlags(event.target.value)}
            />
          </div>

          <div className="space-y-1.5 md:col-span-2">
            <Label>Triage notes</Label>
            <Textarea
              rows={4}
              placeholder="Clinical observations, nursing concerns, and escalation context"
              value={triageNotes}
              onChange={(event) => setTriageNotes(event.target.value)}
            />
          </div>
        </div>

        {error ? <p className="text-sm text-red-600">{error}</p> : null}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="button" onClick={handleSave} disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : "Save and Move to In Consultation"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
