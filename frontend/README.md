# Concept 10 Frontend

Next.js 14 frontend scaffold with:

- TypeScript
- Tailwind CSS
- shadcn/ui base setup
- App Router with `(dashboard)` route group
- Clerk auth guard for multi-tenant clinic access
- TanStack React Query provider
- Axios client with Bearer token + `clinic_id` header injection

## Setup

1. Install dependencies:

   ```bash
   npm install
   ```

2. Create env file:

   ```bash
   copy .env.local.example .env.local
   ```

3. Start dev server:

   ```bash
   npm run dev
   ```

## Key Files

- `app/(dashboard)/layout.tsx`: auth + organization guard, sidebar shell
- `components/app-sidebar.tsx`: nav (Patients, Encounters, Medications, Settings)
- `lib/providers.tsx`: React Query setup
- `lib/axios.ts`: auth token + tenant header injection
- `middleware.ts`: Clerk route protection
