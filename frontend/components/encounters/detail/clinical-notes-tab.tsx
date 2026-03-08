"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { RichTextEditor } from "@/components/ui/rich-text-editor";
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
  useAddNote,
  useAutoSave,
  usePatientEncounters,
  useSignNote,
  useUpdateNote,
} from "@/lib/use-encounter-detail";
import type { Encounter } from "@/types/encounter-queue";
import {
  CheckCircle,
  Clock,
  FileText,
  History,
  Lock,
  Save,
} from "lucide-react";

type Props = {
  encounter: Encounter;
  readOnly: boolean;
  onDirtyChange: (dirty: boolean) => void;
};

function formatTime(d: Date) {
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function renderNoteText(value: string) {
  // Signed note snapshots may contain rich text HTML; render as plain text to avoid script injection.
  return value.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

export function ClinicalNotesTab({ encounter, readOnly, onDirtyChange }: Props) {
  // Find the latest unsigned SOAP note or create new
  const existingNote = useMemo(
    () => encounter.notes.find((n) => n.note_type === "SOAP" && !n.is_signed) ?? null,
    [encounter.notes]
  );

  const [subjective, setSubjective] = useState(existingNote?.subjective ?? "");
  const [objective, setObjective] = useState(existingNote?.objective ?? "");
  const [assessment, setAssessment] = useState(existingNote?.assessment ?? "");
  const [plan, setPlan] = useState(existingNote?.plan ?? "");
  const [isDirty, setIsDirty] = useState(false);
  const [showSignModal, setShowSignModal] = useState(false);
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const [selectedPreviousEncId, setSelectedPreviousEncId] = useState<string>("");

  const addNote = useAddNote(encounter.id);
  const updateNote = useUpdateNote(encounter.id);
  const signNote = useSignNote(encounter.id);
  const { data: patientEncounters } = usePatientEncounters(encounter.patient_id);

  // Sync from server when note changes
  useEffect(() => {
    if (existingNote) {
      setSubjective(existingNote.subjective ?? "");
      setObjective(existingNote.objective ?? "");
      setAssessment(existingNote.assessment ?? "");
      setPlan(existingNote.plan ?? "");
    }
  }, [existingNote]);

  // Track dirty state
  useEffect(() => {
    const dirty =
      subjective !== (existingNote?.subjective ?? "") ||
      objective !== (existingNote?.objective ?? "") ||
      assessment !== (existingNote?.assessment ?? "") ||
      plan !== (existingNote?.plan ?? "");
    setIsDirty(dirty);
    onDirtyChange(dirty);
  }, [subjective, objective, assessment, plan, existingNote, onDirtyChange]);

  // Save function
  const handleSave = useCallback(() => {
    if (readOnly || !isDirty) return;
    const body = { subjective, objective, assessment, plan };
    if (existingNote) {
      updateNote.mutate({ noteId: existingNote.id, ...body });
    } else {
      addNote.mutate({ note_type: "SOAP", ...body });
    }
    setIsDirty(false);
  }, [readOnly, isDirty, subjective, objective, assessment, plan, existingNote, updateNote, addNote]);

  // Auto-save every 30s
  const { lastSaved } = useAutoSave(handleSave, 30_000, isDirty && !readOnly);

  // Ctrl+S handler
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        handleSave();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handleSave]);

  // Copy forward from previous encounter
  const handleCopyForward = useCallback(() => {
    if (!patientEncounters || !selectedPreviousEncId) return;
    const prev = patientEncounters.items.find((e) => e.id === selectedPreviousEncId);
    const prevNote = prev?.notes.find((n) => n.note_type === "SOAP");
    if (prevNote) {
      setSubjective(prevNote.subjective ?? "");
      setObjective(prevNote.objective ?? "");
      setAssessment(prevNote.assessment ?? "");
      setPlan(prevNote.plan ?? "");
    }
  }, [patientEncounters, selectedPreviousEncId]);

  // Sign note
  const handleSign = useCallback(() => {
    if (!existingNote) return;
    handleSave();
    signNote.mutate(existingNote.id, {
      onSuccess: () => setShowSignModal(false),
    });
  }, [existingNote, handleSave, signNote]);

  // Signed notes (version history)
  const signedNotes = useMemo(
    () => encounter.notes.filter((n) => n.is_signed).sort((a, b) => b.version - a.version),
    [encounter.notes]
  );

  // Previous encounters for copy-forward dropdown
  const previousEncounters = useMemo(
    () =>
      patientEncounters?.items.filter(
        (e) => e.id !== encounter.id && e.notes.some((n) => n.note_type === "SOAP")
      ) ?? [],
    [patientEncounters, encounter.id]
  );

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          {/* Copy forward */}
          {previousEncounters.length > 0 && !readOnly && (
            <div className="flex items-center gap-1">
              <Select value={selectedPreviousEncId} onValueChange={setSelectedPreviousEncId}>
                <SelectTrigger className="h-8 w-[180px] text-xs">
                  <SelectValue placeholder="Copy from previous..." />
                </SelectTrigger>
                <SelectContent>
                  {previousEncounters.map((enc) => (
                    <SelectItem key={enc.id} value={enc.id}>
                      {enc.encounter_id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopyForward}
                disabled={!selectedPreviousEncId}
              >
                <FileText className="h-3.5 w-3.5 mr-1" />
                Copy
              </Button>
            </div>
          )}
          {/* Version history */}
          {signedNotes.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowVersionHistory(!showVersionHistory)}
            >
              <History className="h-3.5 w-3.5 mr-1" />
              History ({signedNotes.length})
            </Button>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Save indicator */}
          {lastSaved && (
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Saved at {formatTime(lastSaved)}
            </span>
          )}
          {isDirty && (
            <Badge variant="outline" className="text-xs bg-yellow-50 text-yellow-700">
              Unsaved changes
            </Badge>
          )}
          {!readOnly && (
            <>
              <Button variant="outline" size="sm" onClick={handleSave} disabled={!isDirty}>
                <Save className="h-3.5 w-3.5 mr-1" />
                Save
              </Button>
              <Button
                size="sm"
                onClick={() => setShowSignModal(true)}
                disabled={!existingNote || existingNote.is_signed}
              >
                <Lock className="h-3.5 w-3.5 mr-1" />
                Sign Note
              </Button>
            </>
          )}
        </div>
      </div>

      {/* SOAP editor */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label className="text-xs font-semibold uppercase tracking-wide">Subjective</Label>
          <RichTextEditor
            value={subjective}
            onChange={setSubjective}
            placeholder="Patient's history, symptoms, complaints..."
            className="min-h-[140px]"
            disabled={readOnly}
          />
        </div>
        <div className="space-y-2">
          <Label className="text-xs font-semibold uppercase tracking-wide">Objective</Label>
          <RichTextEditor
            value={objective}
            onChange={setObjective}
            placeholder="Physical exam findings, vitals, lab results..."
            className="min-h-[140px]"
            disabled={readOnly}
          />
        </div>
        <div className="space-y-2">
          <Label className="text-xs font-semibold uppercase tracking-wide">Assessment</Label>
          <RichTextEditor
            value={assessment}
            onChange={setAssessment}
            placeholder="Diagnosis, clinical impression..."
            className="min-h-[140px]"
            disabled={readOnly}
          />
        </div>
        <div className="space-y-2">
          <Label className="text-xs font-semibold uppercase tracking-wide">Plan</Label>
          <RichTextEditor
            value={plan}
            onChange={setPlan}
            placeholder="Treatment plan, orders, follow-up..."
            className="min-h-[140px]"
            disabled={readOnly}
          />
        </div>
      </div>

      {/* Keyboard shortcut hint */}
      {!readOnly && (
        <p className="text-xs text-muted-foreground">
          <kbd className="rounded border px-1 py-0.5 text-[10px] font-mono">Ctrl+S</kbd> to save
        </p>
      )}

      {/* Version history panel */}
      {showVersionHistory && signedNotes.length > 0 && (
        <div className="space-y-3 border-t pt-4">
          <h4 className="text-sm font-semibold flex items-center gap-1.5">
            <History className="h-4 w-4" />
            Signed Note History
          </h4>
          <ScrollArea className="max-h-[400px]">
            <div className="space-y-3">
              {signedNotes.map((note) => (
                <div key={note.id} className="rounded-lg border bg-muted/30 p-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-[10px] bg-green-50 text-green-700">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Signed v{note.version}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {new Date(note.signed_at ?? note.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                    {note.subjective && (
                      <div>
                        <span className="font-medium text-muted-foreground">S: </span>
                        <span>{renderNoteText(note.subjective)}</span>
                      </div>
                    )}
                    {note.objective && (
                      <div>
                        <span className="font-medium text-muted-foreground">O: </span>
                        <span>{renderNoteText(note.objective)}</span>
                      </div>
                    )}
                    {note.assessment && (
                      <div>
                        <span className="font-medium text-muted-foreground">A: </span>
                        <span>{renderNoteText(note.assessment)}</span>
                      </div>
                    )}
                    {note.plan && (
                      <div>
                        <span className="font-medium text-muted-foreground">P: </span>
                        <span>{renderNoteText(note.plan)}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      )}

      {/* Sign confirmation modal */}
      <Dialog open={showSignModal} onOpenChange={setShowSignModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Sign Clinical Note</DialogTitle>
            <DialogDescription>
              Once signed, this note will be locked and cannot be edited. A new
              version will need to be created for any changes. Are you sure you
              want to sign this note?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSignModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleSign} disabled={signNote.isPending}>
              {signNote.isPending ? "Signing..." : "Sign & Lock Note"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
