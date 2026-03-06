import { OrganizationSwitcher } from "@clerk/nextjs";

export default function SelectClinicPage() {
  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="space-y-4 rounded-lg border p-6">
        <h1 className="text-xl font-semibold">Select Clinic</h1>
        <p className="text-sm text-muted-foreground">Choose a clinic workspace to continue.</p>
        <OrganizationSwitcher afterSelectOrganizationUrl="/patients" />
      </div>
    </main>
  );
}
