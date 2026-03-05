"use client";

import axios from "axios";
import { useAuth } from "@clerk/nextjs";
import { useEffect } from "react";
import { useState } from "react";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1",
});

export function useApiClient() {
  const { getToken, orgId, userId, isLoaded } = useAuth();
  const [isInterceptorReady, setIsInterceptorReady] = useState(false);
  const isReady = isLoaded && Boolean(userId) && Boolean(orgId) && isInterceptorReady;

  useEffect(() => {
    setIsInterceptorReady(false);

    const interceptor = api.interceptors.request.use(async (config) => {
      const token = await getToken();

      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      if (orgId) {
        config.headers["clinic_id"] = orgId;
        config.headers["x-clinic-id"] = orgId;
      }

      if (userId) {
        config.headers["x-user-id"] = userId;
      }

      return config;
    });

    setIsInterceptorReady(true);

    return () => {
      api.interceptors.request.eject(interceptor);
      setIsInterceptorReady(false);
    };
  }, [getToken, orgId, userId]);

  return { api, isReady };
}
