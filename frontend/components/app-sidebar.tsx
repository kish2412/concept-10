"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton } from "@clerk/nextjs";
import { ClipboardList, LayoutDashboard, Pill, Settings, Users } from "lucide-react";

import { cn } from "@/lib/utils";
import { usePermission } from "@/lib/permission-context";

const navItems = [
  { href: "/patients",   label: "Patients",   icon: Users          },
  { href: "/encounters", label: "Encounters", icon: ClipboardList  },
  { href: "/queue",      label: "Queue",      icon: LayoutDashboard },
  { href: "/medications",label: "Medications",icon: Pill           },
  { href: "/settings",   label: "Settings",   icon: Settings       },
];

export function AppSidebar() {
  const pathname = usePathname();

  // Replace OrganizationSwitcher — get clinic name from our own context
  const { clinicName, systemRole } = usePermission();

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden w-[260px] shrink-0 flex-col border-r bg-muted/30 p-4 md:flex h-screen sticky top-0">

        {/* Clinic name — replaces <OrganizationSwitcher /> */}
        <div className="mb-6 rounded-md border bg-background px-3 py-2">
          <p className="text-xs text-muted-foreground">Clinic</p>
          <p className="truncate text-sm font-medium">
            {clinicName ?? "Loading..."}
          </p>
          {systemRole && (
            <p className="mt-0.5 text-[10px] capitalize text-muted-foreground">
              {systemRole}
            </p>
          )}
        </div>

        <nav className="space-y-1">
          {navItems.map((item) => {
            const isActive = pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-muted",
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto pt-4">
          <UserButton afterSignOutUrl="/sign-in" />
        </div>
      </aside>

      {/* Mobile bottom nav */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around border-t bg-background py-2 md:hidden">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-col items-center gap-0.5 rounded-md px-2 py-1 text-[10px]",
                isActive ? "text-primary" : "text-muted-foreground",
              )}
            >
              <Icon className="h-5 w-5" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
