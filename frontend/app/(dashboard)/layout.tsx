import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";

import { AppSidebar } from "@/components/app-sidebar";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { userId, orgId } = await (await auth());

  if (!userId) {
    redirect("/sign-in");
  }

  if (!orgId) {
    redirect("/select-clinic");
  }

  return (
    <div className="grid min-h-screen grid-cols-[260px_1fr]">
      <AppSidebar />
      <main className="p-6">{children}</main>
    </div>
  );
}
