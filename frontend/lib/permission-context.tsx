"use client";
/**
 * frontend/lib/permission-context.tsx
 * ─────────────────────────────────────
 * Replaces all Clerk org/role checks (useOrganization, orgId, etc.)
 * with data from your own API.
 *
 * Wrap the app with <PermissionProvider> in app/layout.tsx (see bottom of file).
 */

import {
  createContext, useContext, useEffect, useState, useCallback, ReactNode,
} from "react";
import { useAuth } from "@clerk/nextjs";

// ── Types ─────────────────────────────────────────────────────────────

export type Action   = "create" | "read" | "update" | "delete";
export type Resource =
  | "patient" | "patient_history" | "clinical_notes" | "chief_complaint"
  | "vitals" | "prescription" | "investigation" | "nursing_notes"
  | "queue" | "appointment" | "checkin"
  | "user_management" | "clinic_settings" | "reports" | "audit_logs"
  | "invoice" | "payment" | "fee_template";

export type SystemRole =
  | "admin" | "receptionist" | "nurse" | "doctor" | "consultant" | "billing";

interface CustomRoleInfo { id: string; name: string; slug: string; color: string | null; }

interface Features { allow_custom_roles: boolean; ai_enabled: boolean; }

interface PermissionState {
  isLoaded:        boolean;
  isAuthenticated: boolean;   // true = has valid token AND is onboarded to a clinic
  userId:          string | null;
  clinicId:        string | null;
  clinicName:      string | null;
  systemRole:      SystemRole | null;
  customRoles:     CustomRoleInfo[];
  features:        Features;
  can:             (action: Action, resource: Resource) => boolean;
  hasRole:         (...roles: SystemRole[]) => boolean;
  hasCustomRole:   (slug: string) => boolean;
  refresh:         () => void;
}

// ── Context ───────────────────────────────────────────────────────────

const PermissionContext = createContext<PermissionState>({
  isLoaded: false, isAuthenticated: false,
  userId: null, clinicId: null, clinicName: null,
  systemRole: null, customRoles: [],
  features: { allow_custom_roles: false, ai_enabled: false },
  can: () => false, hasRole: () => false, hasCustomRole: () => false,
  refresh: () => {},
});

// ── Provider ──────────────────────────────────────────────────────────

export function PermissionProvider({ children }: { children: ReactNode }) {
  const { isLoaded: clerkLoaded, isSignedIn, getToken } = useAuth();
  const [state, setState] = useState<PermissionState>({
    isLoaded: false, isAuthenticated: false,
    userId: null, clinicId: null, clinicName: null,
    systemRole: null, customRoles: [],
    features: { allow_custom_roles: false, ai_enabled: false },
    can: () => false, hasRole: () => false, hasCustomRole: () => false,
    refresh: () => {},
  });

  const load = useCallback(async () => {
    if (!isSignedIn) {
      setState(s => ({ ...s, isLoaded: true, isAuthenticated: false }));
      return;
    }

    try {
      const token = await getToken();
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/me/permissions`,
        { headers: { Authorization: `Bearer ${token}` } },
      );

      if (res.status === 401 || res.status === 404) {
        // Signed in with Clerk but not yet onboarded to a clinic
        setState(s => ({ ...s, isLoaded: true, isAuthenticated: false }));
        return;
      }

      if (!res.ok) throw new Error(`/me/permissions returned ${res.status}`);

      const data = await res.json();

      const permSet = new Set<string>(
        data.permissions.map((p: { action: string; resource: string }) =>
          `${p.action}:${p.resource}`
        )
      );

      setState({
        isLoaded:        true,
        isAuthenticated: true,
        userId:          data.user_id,
        clinicId:        data.clinic_id,
        clinicName:      data.clinic_name,
        systemRole:      data.system_role,
        customRoles:     data.custom_roles ?? [],
        features:        data.features ?? { allow_custom_roles: false, ai_enabled: false },
        can:             (action, resource) => permSet.has(`${action}:${resource}`),
        hasRole:         (...roles) => roles.includes(data.system_role),
        hasCustomRole:   (slug) => (data.custom_roles ?? []).some((r: CustomRoleInfo) => r.slug === slug),
        refresh:         load,
      });
    } catch (err) {
      console.error("PermissionProvider: failed to load permissions", err);
      setState(s => ({ ...s, isLoaded: true, isAuthenticated: false }));
    }
  }, [isSignedIn, getToken]);

  useEffect(() => {
    if (clerkLoaded) load();
  }, [clerkLoaded, load]);

  // Expose refresh on the state so consumers can trigger a reload
  const value = { ...state, refresh: load };

  return (
    <PermissionContext.Provider value={value}>
      {children}
    </PermissionContext.Provider>
  );
}

// ── Hooks ─────────────────────────────────────────────────────────────

export function usePermission() {
  return useContext(PermissionContext);
}

/** Returns true while permissions are still loading (spinner guard). */
export function usePermissionLoading() {
  return !useContext(PermissionContext).isLoaded;
}

// ── Guard components ──────────────────────────────────────────────────

interface CanProps {
  action: Action;
  resource: Resource;
  children: ReactNode;
  fallback?: ReactNode;
}
export function Can({ action, resource, children, fallback = null }: CanProps) {
  const { can } = usePermission();
  return <>{can(action, resource) ? children : fallback}</>;
}

interface HasRoleProps {
  roles: SystemRole[];
  children: ReactNode;
  fallback?: ReactNode;
}
export function HasRole({ roles, children, fallback = null }: HasRoleProps) {
  const { hasRole } = usePermission();
  return <>{hasRole(...roles) ? children : fallback}</>;
}

/*
─────────────────────────────────────────────────────────────────────────────
USAGE:  Add PermissionProvider to frontend/app/layout.tsx

import { PermissionProvider } from "@/lib/permission-context";

export default function RootLayout({ children }) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body>
          <Providers>
            <PermissionProvider>     ← add this
              {children}
            </PermissionProvider>
          </Providers>
        </body>
      </html>
    </ClerkProvider>
  );
}
─────────────────────────────────────────────────────────────────────────────
*/
