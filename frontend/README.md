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

## Encounter Detail Features

Route: `app/(dashboard)/encounters/[id]/page.tsx`

- `Overview`: header metadata, status badge, vitals trend cards, allergies/chronic/current meds sidebars
- `Clinical Notes (SOAP)`: rich text S/O/A/P, autosave (30s), saved timestamp, copy-forward, sign modal + lock, signed version history
- `Diagnoses`: debounced ICD-10 autocomplete, diagnosis typing, chronic flag, remove confirmation
- `Orders`: type-based dynamic fields, grouped list by type, status tracker + update, inline result viewer (text/PDF), STAT/URGENT badges
- `Prescriptions`: drug autocomplete (name + generic), full Rx form fields, interaction warning banner, print/send actions, controlled-substance indicator
- `Disposition`: disposition types, follow-up days/date UI, rich text instruction areas, education material selector with PDF links, complete encounter validations + discharge modal
- `Global`: keyboard shortcut hints, unsaved-change warning, timeline with timestamps, write actions disabled in discharged/read-only mode

Known gap:
- Follow-up specific date is currently UI-only and not persisted to backend yet.
