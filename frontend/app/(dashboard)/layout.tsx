"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AppSidebar } from "@/components/app-sidebar";
import { usePermission } from "@/lib/permission-context";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { isLoaded, isAuthenticated } = usePermission();
  const router = useRouter();

  useEffect(() => {
    if (isLoaded && !isAuthenticated) {
      router.replace("/select-clinic");
    }
  }, [isLoaded, isAuthenticated, router]);

  if (!isLoaded) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="flex min-h-screen">
      <AppSidebar />
      <main className="flex-1 overflow-hidden p-4 pb-16 md:p-6 md:pb-6">
        {children}
      </main>
    </div>
  );
}
