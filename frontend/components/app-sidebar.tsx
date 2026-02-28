"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { OrganizationSwitcher, UserButton } from "@clerk/nextjs";
import { ClipboardList, Pill, Settings, Users } from "lucide-react";

import { cn } from "@/lib/utils";

const navItems = [
  { href: "/patients", label: "Patients", icon: Users },
  { href: "/encounters", label: "Encounters", icon: ClipboardList },
  { href: "/medications", label: "Medications", icon: Pill },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen flex-col border-r bg-muted/30 p-4">
      <div className="mb-6">
        <OrganizationSwitcher hidePersonal afterSelectOrganizationUrl="/patients" />
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
                isActive ? "bg-primary text-primary-foreground" : "hover:bg-muted"
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
  );
}
