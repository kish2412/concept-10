"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useApiClient } from "@/lib/axios";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";

type PatientBackground = {
  medical_history: string | null;
  surgical_history: string | null;
  family_history: string | null;
  social_history: string | null;
  current_medications: string | null;
  immunizations: Record<string, unknown>;
};

type PatientBackgroundPayload = {
  medical_history?: string;
  surgical_history?: string;
  family_history?: string;
  social_history?: string;
  current_medications?: string;
  immunizations?: Record<string, unknown>;
};

type Props = {
  patientId: string;
};

const initialState = {
  medical_history: "",
  surgical_history: "",
  family_history: "",
  social_history: "",
  current_medications: "",
  immunizations: "{}",
};

export function PatientBackgroundTab({ patientId }: Props) {
  const { api, isReady } = useApiClient();
  const queryClient = useQueryClient();
  const [formState, setFormState] = useState(initialState);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["patient-background", patientId],
    queryFn: async () => {
      const response = await api.get<PatientBackground>(`/patients/${patientId}/background`);
      return response.data;
    },
    enabled: Boolean(patientId) && isReady,
  });

  useEffect(() => {
    if (!data) {
      return;
    }

    setFormState({
      medical_history: data.medical_history ?? "",
      surgical_history: data.surgical_history ?? "",
      family_history: data.family_history ?? "",
      social_history: data.social_history ?? "",
      current_medications: data.current_medications ?? "",
      immunizations: JSON.stringify(data.immunizations ?? {}, null, 2),
    });
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: async (payload: PatientBackgroundPayload) => {
      if (!isReady) {
        throw new Error("Authentication context is not ready");
      }
      await api.put(`/patients/${patientId}/background`, payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["patient-background", patientId] });
    },
  });

  function onTextBlur(field: keyof typeof formState) {
    return () => {
      if (field === "immunizations") {
        try {
          const parsed = JSON.parse(formState.immunizations || "{}");
          saveMutation.mutate({ immunizations: parsed });
        } catch {
          return;
        }
        return;
      }

      saveMutation.mutate({
        [field]: formState[field],
      });
    };
  }

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading background...</p>;
  }

  if (isError) {
    return <p className="text-sm text-red-600">Failed to load patient background.</p>;
  }

  return (
    <div className="space-y-3 rounded-md border p-4">
      <Tabs defaultValue="medical" className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="medical">Medical History</TabsTrigger>
          <TabsTrigger value="surgical">Surgical</TabsTrigger>
          <TabsTrigger value="family">Family</TabsTrigger>
          <TabsTrigger value="social">Social</TabsTrigger>
          <TabsTrigger value="immunizations">Immunizations</TabsTrigger>
        </TabsList>

        <TabsContent value="medical" className="space-y-3">
          <Textarea
            value={formState.medical_history}
            onChange={(e) => setFormState((prev) => ({ ...prev, medical_history: e.target.value }))}
            onBlur={onTextBlur("medical_history")}
            placeholder="Medical history"
          />
          <Textarea
            value={formState.current_medications}
            onChange={(e) => setFormState((prev) => ({ ...prev, current_medications: e.target.value }))}
            onBlur={onTextBlur("current_medications")}
            placeholder="Current medications"
          />
        </TabsContent>

        <TabsContent value="surgical">
          <Textarea
            value={formState.surgical_history}
            onChange={(e) => setFormState((prev) => ({ ...prev, surgical_history: e.target.value }))}
            onBlur={onTextBlur("surgical_history")}
            placeholder="Surgical history"
          />
        </TabsContent>

        <TabsContent value="family">
          <Textarea
            value={formState.family_history}
            onChange={(e) => setFormState((prev) => ({ ...prev, family_history: e.target.value }))}
            onBlur={onTextBlur("family_history")}
            placeholder="Family history"
          />
        </TabsContent>

        <TabsContent value="social">
          <Textarea
            value={formState.social_history}
            onChange={(e) => setFormState((prev) => ({ ...prev, social_history: e.target.value }))}
            onBlur={onTextBlur("social_history")}
            placeholder="Social history"
          />
        </TabsContent>

        <TabsContent value="immunizations">
          <Textarea
            value={formState.immunizations}
            onChange={(e) => setFormState((prev) => ({ ...prev, immunizations: e.target.value }))}
            onBlur={onTextBlur("immunizations")}
            placeholder='{"covid": "2024-01-20"}'
          />
        </TabsContent>
      </Tabs>

      {saveMutation.isPending ? <p className="text-xs text-muted-foreground">Saving...</p> : null}
      {saveMutation.isError ? <p className="text-xs text-red-600">Auto-save failed.</p> : null}
      {saveMutation.isSuccess ? <p className="text-xs text-muted-foreground">Saved</p> : null}
    </div>
  );
}
