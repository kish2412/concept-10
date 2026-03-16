import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";

import "./globals.css";
import { Providers } from "@/lib/providers";
import { PermissionProvider } from "@/lib/permission-context";

export const metadata: Metadata = {
  title: "Concept 10 Dashboard",
  description: "Multi-tenant clinic management",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en" suppressHydrationWarning>
        <body suppressHydrationWarning>
          <Providers>
            <PermissionProvider>
              {children}
            </PermissionProvider>
          </Providers>
        </body>
      </html>
    </ClerkProvider>
  );
}
