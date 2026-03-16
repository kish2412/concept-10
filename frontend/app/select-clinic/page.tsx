"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { usePermission } from "@/lib/permission-context";

interface Clinic {
  id: string;
  name: string;
  slug: string | null;
}

export default function SelectClinicPage() {
  const router = useRouter();
  const { getToken, isSignedIn, isLoaded: clerkLoaded } = useAuth();
  const { isLoaded, isAuthenticated, refresh } = usePermission();

  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newClinicName, setNewClinicName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // If not signed in, send to sign-in first
  useEffect(() => {
    if (clerkLoaded && !isSignedIn) {
      router.replace("/sign-in");
    }
  }, [clerkLoaded, isSignedIn, router]);

  // If user is already onboarded to a clinic, skip this page
  useEffect(() => {
    if (isLoaded && isAuthenticated) {
      router.replace("/patients");
    }
  }, [isLoaded, isAuthenticated, router]);

  // Fetch clinics this user belongs to (may be empty for new users)
  useEffect(() => {
    if (!isSignedIn) return;

    (async () => {
      try {
        const token = await getToken();
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_BASE_URL}/tenants/mine`,
          { headers: { Authorization: `Bearer ${token}` } },
        );
        if (res.ok) {
          setClinics(await res.json());
        }
      } catch {
        // No clinics found — show create option
      } finally {
        setLoading(false);
      }
    })();
  }, [isSignedIn, getToken]);

  async function handleSelectClinic(clinicId: string) {
    // Selecting a clinic triggers a permission context refresh.
    // The backend will now return this clinic's data for /me/permissions.
    // NOTE: For multi-clinic users, you would store the selected clinic ID
    // in a cookie here so the backend knows which clinic to use.
    // For single-clinic users (most cases), the backend picks the only clinic.
    refresh();
    // refresh() triggers /me/permissions reload → isAuthenticated becomes true
    // → the useEffect above redirects to /patients
  }

  async function handleCreateClinic() {
    if (!newClinicName.trim()) return;
    setSubmitting(true);
    setError(null);

    try {
      const token = await getToken();
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/tenants`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ name: newClinicName.trim() }),
        },
      );

      if (!res.ok) {
        const data = await res.json();
        setError(data.detail ?? "Failed to create clinic");
        return;
      }

      // Clinic created — refresh permission context
      // This will re-fetch /me/permissions which now returns the new clinic
      refresh();
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  // Still checking auth state
  if (!clerkLoaded || !isSignedIn || !isLoaded || (isLoaded && isAuthenticated)) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-md space-y-4 rounded-lg border p-6">
        <h1 className="text-xl font-semibold">Select Clinic</h1>
        <p className="text-sm text-muted-foreground">
          Choose a clinic workspace to continue.
        </p>

        {loading ? (
          <p className="text-sm text-muted-foreground">Loading...</p>

        ) : clinics.length > 0 && !creating ? (
          // User belongs to one or more clinics — show list
          <div className="space-y-2">
            {clinics.map((clinic) => (
              <button
                key={clinic.id}
                onClick={() => handleSelectClinic(clinic.id)}
                className="w-full rounded-md border px-4 py-3 text-left text-sm hover:bg-muted transition-colors"
              >
                {clinic.name}
              </button>
            ))}
            <button
              onClick={() => setCreating(true)}
              className="w-full rounded-md border border-dashed px-4 py-3 text-left text-sm text-muted-foreground hover:bg-muted transition-colors"
            >
              + Create a new clinic
            </button>
          </div>

        ) : (
          // No clinics yet, or user clicked "Create new"
          <div className="space-y-3">
            {clinics.length > 0 && (
              <button
                onClick={() => setCreating(false)}
                className="text-sm text-muted-foreground hover:underline"
              >
                ← Back
              </button>
            )}
            <div>
              <label className="text-sm font-medium" htmlFor="clinic-name">
                Clinic name
              </label>
              <input
                id="clinic-name"
                type="text"
                placeholder="e.g. Sunrise Medical Centre"
                value={newClinicName}
                onChange={(e) => setNewClinicName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreateClinic()}
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}

            <button
              onClick={handleCreateClinic}
              disabled={submitting || !newClinicName.trim()}
              className="w-full rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {submitting ? "Creating..." : "Create clinic"}
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
