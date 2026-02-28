"use client";

import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";

import { useApiClient } from "@/lib/axios";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Patient = {
  id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  phone: string | null;
  email: string | null;
  address: string | null;
  blood_type: string | null;
  allergies: string[];
  is_active: boolean;
  last_visit?: string | null;
};

type PatientsListResponse = {
  items: Patient[];
  total: number;
  page: number;
  size: number;
};

type PatientPayload = {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  blood_type?: string | null;
  allergies: string[];
  is_active: boolean;
};

const patientFormSchema = z.object({
  first_name: z.string().min(1, "First name is required"),
  last_name: z.string().min(1, "Last name is required"),
  date_of_birth: z.string().min(1, "Date of birth is required"),
  gender: z.string().min(1, "Gender is required"),
  phone: z.string().optional(),
  email: z.string().email("Invalid email address").or(z.literal("")).optional(),
  address: z.string().optional(),
  blood_type: z.string().optional(),
  allergies: z.string().optional(),
});

type PatientFormValues = z.infer<typeof patientFormSchema>;

const defaultFormValues: PatientFormValues = {
  first_name: "",
  last_name: "",
  date_of_birth: "",
  gender: "",
  phone: "",
  email: "",
  address: "",
  blood_type: "",
  allergies: "",
};

function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleDateString();
}

export default function PatientsPage() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState("");
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [editingPatient, setEditingPatient] = useState<Patient | null>(null);

  const form = useForm<PatientFormValues>({
    resolver: zodResolver(patientFormSchema),
    defaultValues: defaultFormValues,
  });

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["patients", search],
    queryFn: async () => {
      const response = await api.get<PatientsListResponse>("/patients", {
        params: {
          page: 1,
          size: 50,
          search: search || undefined,
        },
      });
      return response.data;
    },
  });

  const createPatientMutation = useMutation({
    mutationFn: async (payload: PatientPayload) => {
      await api.post("/patients", payload);
    },
    onSuccess: async () => {
      setIsDrawerOpen(false);
      setEditingPatient(null);
      form.reset(defaultFormValues);
      await queryClient.invalidateQueries({ queryKey: ["patients"] });
    },
  });

  const updatePatientMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: PatientPayload }) => {
      await api.put(`/patients/${id}`, payload);
    },
    onSuccess: async () => {
      setIsDrawerOpen(false);
      setEditingPatient(null);
      form.reset(defaultFormValues);
      await queryClient.invalidateQueries({ queryKey: ["patients"] });
    },
  });

  const patients = useMemo(() => data?.items ?? [], [data?.items]);
  const isSubmitting = createPatientMutation.isPending || updatePatientMutation.isPending;
  const submitError = createPatientMutation.isError || updatePatientMutation.isError;
  const isEditMode = Boolean(editingPatient);

  function resetFormState(open: boolean) {
    setIsDrawerOpen(open);
    if (!open) {
      setEditingPatient(null);
      form.reset(defaultFormValues);
    }
  }

  function toPayload(values: PatientFormValues): PatientPayload {
    return {
      first_name: values.first_name,
      last_name: values.last_name,
      date_of_birth: values.date_of_birth,
      gender: values.gender,
      phone: values.phone?.trim() || null,
      email: values.email?.trim() || null,
      address: values.address?.trim() || null,
      blood_type: values.blood_type?.trim() || null,
      allergies: (values.allergies || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
      is_active: editingPatient?.is_active ?? true,
    };
  }

  function openAddDrawer() {
    setEditingPatient(null);
    form.reset(defaultFormValues);
    setIsDrawerOpen(true);
  }

  function openEditDrawer(patient: Patient) {
    setEditingPatient(patient);
    form.reset({
      first_name: patient.first_name,
      last_name: patient.last_name,
      date_of_birth: patient.date_of_birth,
      gender: patient.gender,
      phone: patient.phone ?? "",
      email: patient.email ?? "",
      address: patient.address ?? "",
      blood_type: patient.blood_type ?? "",
      allergies: (patient.allergies || []).join(", "),
    });
    setIsDrawerOpen(true);
  }

  function onSubmit(values: PatientFormValues) {
    const payload = toPayload(values);
    if (editingPatient) {
      updatePatientMutation.mutate({ id: editingPatient.id, payload });
      return;
    }
    createPatientMutation.mutate(payload);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Patients</h1>

        <Sheet open={isDrawerOpen} onOpenChange={resetFormState}>
          <SheetTrigger asChild>
            <Button onClick={openAddDrawer}>Add Patient</Button>
          </SheetTrigger>
          <SheetContent>
            <SheetHeader>
              <SheetTitle>{isEditMode ? "Edit Patient" : "Add Patient"}</SheetTitle>
              <SheetDescription>
                {isEditMode ? "Update patient details." : "Create a new patient record."}
              </SheetDescription>
            </SheetHeader>

            <Form {...form}>
              <form className="mt-6 space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
                <FormField
                  control={form.control}
                  name="first_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>First name</FormLabel>
                      <FormControl>
                        <Input placeholder="First name" {...field} />
                      </FormControl>
                      <FormMessage name="first_name" />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="last_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Last name</FormLabel>
                      <FormControl>
                        <Input placeholder="Last name" {...field} />
                      </FormControl>
                      <FormMessage name="last_name" />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="date_of_birth"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Date of birth</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} />
                      </FormControl>
                      <FormMessage name="date_of_birth" />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="gender"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Gender</FormLabel>
                      <FormControl>
                        <Input placeholder="Gender" {...field} />
                      </FormControl>
                      <FormMessage name="gender" />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="phone"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Phone</FormLabel>
                      <FormControl>
                        <Input placeholder="Phone" {...field} value={field.value ?? ""} />
                      </FormControl>
                      <FormMessage name="phone" />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Email</FormLabel>
                      <FormControl>
                        <Input placeholder="Email" {...field} value={field.value ?? ""} />
                      </FormControl>
                      <FormMessage name="email" />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="address"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Address</FormLabel>
                      <FormControl>
                        <Input placeholder="Address" {...field} value={field.value ?? ""} />
                      </FormControl>
                      <FormMessage name="address" />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="blood_type"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Blood type</FormLabel>
                      <FormControl>
                        <Input placeholder="Blood type" {...field} value={field.value ?? ""} />
                      </FormControl>
                      <FormMessage name="blood_type" />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="allergies"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Allergies</FormLabel>
                      <FormControl>
                        <Input placeholder="Comma separated allergies" {...field} value={field.value ?? ""} />
                      </FormControl>
                      <FormMessage name="allergies" />
                    </FormItem>
                  )}
                />

                {submitError ? <p className="text-sm text-red-600">Failed to save patient. Please try again.</p> : null}

                <Button type="submit" className="w-full" disabled={isSubmitting}>
                  {isSubmitting ? "Saving..." : isEditMode ? "Update Patient" : "Save Patient"}
                </Button>
              </form>
            </Form>
          </SheetContent>
        </Sheet>
      </div>

      <Input
        placeholder="Search by name or phone"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="max-w-sm"
      />

      {isLoading ? <p className="text-sm text-muted-foreground">Loading patients...</p> : null}

      {isError ? (
        <p className="text-sm text-red-600">Error loading patients: {(error as Error).message || "Unknown error"}</p>
      ) : null}

      {!isLoading && !isError ? (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>DOB</TableHead>
                <TableHead>Phone</TableHead>
                <TableHead>Last visit</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {patients.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">
                    No patients found.
                  </TableCell>
                </TableRow>
              ) : (
                patients.map((patient) => (
                  <TableRow key={patient.id}>
                    <TableCell>
                      <button
                        type="button"
                        className="font-medium hover:underline"
                        onClick={() => openEditDrawer(patient)}
                      >
                        {`${patient.first_name} ${patient.last_name}`}
                      </button>
                    </TableCell>
                    <TableCell>{formatDate(patient.date_of_birth)}</TableCell>
                    <TableCell>{patient.phone || "-"}</TableCell>
                    <TableCell>{formatDate(patient.last_visit)}</TableCell>
                    <TableCell>
                      <Badge variant={patient.is_active ? "default" : "secondary"}>
                        {patient.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      ) : null}
    </div>
  );
}
