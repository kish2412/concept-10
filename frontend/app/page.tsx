import Link from "next/link";

export default async function HomePage() {
  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="space-y-4 text-center">
        <h1 className="text-3xl font-semibold">Concept 10</h1>
        <p className="text-muted-foreground">Sign in to access your clinic dashboard.</p>
        <Link className="inline-flex rounded-md bg-primary px-4 py-2 text-primary-foreground" href="/sign-in">
          Go to Sign In
        </Link>
      </div>
    </main>
  );
}
