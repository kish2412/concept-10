"use client";

/** Axios client configured with Clerk auth and clinic context. */

import axios from "axios";
import { useAuth } from "@clerk/nextjs";
import { useEffect, useState } from "react";
import { usePermission } from "@/lib/permission-context";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL,
});

export function useApiClient() {
  const { getToken, isLoaded: clerkLoaded } = useAuth();
  const { clinicId, isAuthenticated } = usePermission();
  const [ready, setReady] = useState(false);

  const isReady = clerkLoaded && isAuthenticated && Boolean(clinicId) && ready;

  useEffect(() => {
    setReady(false);

    const id = api.interceptors.request.use(async (config) => {
      const token = await getToken();
      if (token) config.headers.Authorization = `Bearer ${token}`;
      if (clinicId) {
        config.headers["x-clinic-id"] = clinicId;
        config.headers["clinic_id"] = clinicId;
      }
      return config;
    });

    setReady(true);

    return () => {
      api.interceptors.request.eject(id);
      setReady(false);
    };
  }, [getToken, clinicId]);

  return { api, isReady };
}
