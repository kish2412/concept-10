import { AppSidebar } from "@/components/app-sidebar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <AppSidebar />
      <main className="flex-1 overflow-hidden p-4 pb-16 md:p-6 md:pb-6">{children}</main>
    </div>
  );
}
