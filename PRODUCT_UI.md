# UI/UX Enhancement Requirements
## Outpatient Management System (OMS) — Multi-Tenant SaaS

---

## 1. Current State Summary

| Area | Status |
|------|--------|
| Auth | Clerk (sign-in, sign-up, org switcher) — working |
| Patients | CRUD table + medical background tabs — working |
| Encounters | Placeholder page |
| Medications | Placeholder page |
| Settings | Placeholder page |
| Layout | Fixed 260px sidebar + content grid — desktop only |
| Styling | Tailwind + shadcn/ui (Radix), HSL CSS variables |
| i18n | Not implemented |
| Responsive | Not implemented (hardcoded `grid-cols-[260px_1fr]`) |

---

## 2. Design Principles

1. **Clinical-first** — Every interaction is optimized for speed in a busy clinic environment. Minimize clicks, maximize scanability.
2. **Mobile-ready** — Doctors round with iPads, receptionists may use phones. Every screen must work at 320px–2560px.
3. **Accessible** — WCAG 2.1 AA compliance. Proper contrast ratios, focus management, screen reader support (Radix already provides this foundation).
4. **Bilingual by default** — English (LTR) and Arabic (RTL) as first-class languages. Layout must flip correctly.
5. **Consistent** — Single design language across all modules. No per-page custom styling decisions.

---

## 3. Responsive Layout System

### 3.1 Breakpoints

| Token | Width | Target Device |
|-------|-------|---------------|
| `sm` | ≥ 640px | Large phones (landscape) |
| `md` | ≥ 768px | iPad Mini / tablets (portrait) |
| `lg` | ≥ 1024px | iPad Pro / small laptops |
| `xl` | ≥ 1280px | Desktop monitors |
| `2xl` | ≥ 1536px | Wide monitors |

### 3.2 Dashboard Shell (replaces current fixed grid)

| Viewport | Sidebar | Behavior |
|----------|---------|----------|
| **< 768px** (phone) | Hidden — hamburger icon in top bar | Sheet overlay, swipe-to-close |
| **768–1023px** (tablet portrait) | Collapsed rail (64px) — icons only | Expand on hover or tap, tooltip labels |
| **≥ 1024px** (tablet landscape / desktop) | Full sidebar (256px) | Always visible, collapsible via toggle |

**Top bar** (visible on all viewports):
- Left: Hamburger (mobile) or sidebar toggle (desktop) + Clinic name (from Clerk org)
- Center: Page title (mobile only — on desktop the page handles its own heading)
- Right: Language toggle + Notifications bell + `<UserButton />`

### 3.3 Content Area

- Max content width: `max-w-7xl` (1280px) centered with `mx-auto`
- Horizontal padding: `px-4` (mobile), `px-6` (tablet), `px-8` (desktop)
- Vertical spacing between sections: `space-y-6`

---

## 4. Multi-Language (i18n) Requirements

### 4.1 Supported Languages

| Language | Code | Direction | Script |
|----------|------|-----------|--------|
| English | `en` | LTR | Latin |
| Arabic | `ar` | RTL | Arabic |

### 4.2 Implementation Approach

- **Library:** `next-intl` (Next.js native i18n with App Router support)
- **Translation files:** `messages/en.json`, `messages/ar.json`
- **Namespace structure:**

```
{
  "common": { "save", "cancel", "delete", "search", "loading", "error" ... },
  "nav": { "patients", "encounters", "medications", "settings" },
  "patients": { "title", "addPatient", "firstName", "lastName", ... },
  "encounters": { ... },
  "medications": { ... },
  "settings": { ... },
  "auth": { "signIn", "signUp", "signOut", "selectClinic" },
  "errors": { "network", "permissionDenied", "sessionExpired", ... },
  "validation": { "required", "invalidEmail", "minLength", ... }
}
```

### 4.3 RTL Layout Rules

- `<html dir="rtl" lang="ar">` set dynamically based on locale
- Sidebar flips to right side
- All `ml-*` / `mr-*` replaced with `ms-*` / `me-*` (logical properties)
- All `left-*` / `right-*` replaced with `start-*` / `end-*`
- Icons that imply direction (arrows, chevrons) must flip
- Tables remain LTR for numeric columns (dates, amounts) but text columns flip
- Form labels appear above inputs (no side-by-side label-input in RTL)

### 4.4 Language Switcher

- Position: top bar, right side (before user avatar)
- Toggle button showing current language code (`EN` / `عر`)
- Persisted in `localStorage` and Clerk user metadata
- Switching language does NOT reload the page (client-side swap)

### 4.5 Medical Terminology

- Clinical terms (diagnosis names, drug names, lab test names) stay in **English** regardless of UI language
- Patient names stored in both `name` (English) and `name_ar` (Arabic) — display based on current locale
- Date format: `DD/MM/YYYY` for Arabic, `MM/DD/YYYY` for English (configurable per clinic in settings)

---

## 5. Component Library Enhancements

### 5.1 New UI Components Needed

| Component | Purpose | Responsive Behavior |
|-----------|---------|---------------------|
| **CommandMenu** (⌘K) | Global search — patients, encounters, commands | Full-screen on mobile, centered modal on desktop |
| **DataTable** | Sortable, filterable, paginated table with column visibility | Horizontal scroll on mobile, card view option |
| **Card** | Content container for dashboard widgets, patient summary | Stack vertically on mobile |
| **Dialog/Modal** | Confirmations, quick actions | Full-screen on mobile (sheet-style), centered on desktop |
| **Select/Combobox** | Dropdowns for gender, blood type, doctor selection | Native select on mobile for better UX |
| **DatePicker** | Date of birth, appointment dates | Native date input on mobile, calendar popover on desktop |
| **Toast/Sonner** | Success/error/warning notifications | Bottom-center on mobile, bottom-right on desktop |
| **Skeleton** | Loading placeholders for all data-fetching states | Match the component shape being loaded |
| **Avatar** | User/patient photos with fallback initials | Consistent sizing across viewports |
| **DropdownMenu** | Row actions (edit, delete, view) | Bottom sheet on mobile, popover on desktop |
| **Breadcrumb** | Navigation context on inner pages | Truncated with ellipsis on mobile |
| **EmptyState** | No-data illustrations for tables/lists | Centered, responsive illustration |
| **StatusIndicator** | Patient status, appointment status | Color-coded dot + label |
| **Stepper** | Multi-step forms (new encounter flow) | Horizontal on desktop, vertical on mobile |

### 5.2 Existing Components — Upgrades

| Component | Enhancement |
|-----------|-------------|
| **Button** | Add `icon` variant (square), `loading` state with spinner, `destructive` variant |
| **Badge** | Add `success`, `warning`, `destructive`, `outline` variants |
| **Table** | Add responsive card view for mobile, sticky header, row selection |
| **Sheet** | Add `side` prop (`left`/`right`/`bottom`), responsive sizing |
| **Input** | Add `startIcon`/`endIcon` slots, `error` state styling |
| **Textarea** | Add character count, auto-resize |
| **Tabs** | Scrollable tab list on mobile (overflow-x-auto) |

---

## 6. Page-by-Page Requirements

### 6.1 Landing Page (`/`)

- Full-screen hero with clinic illustration or gradient background
- Clinic branding area (logo + name)
- "Sign In" and "Sign Up" CTAs
- Language toggle in top-right corner
- Responsive: stacks vertically on mobile, side-by-side on desktop

### 6.2 Select Clinic (`/select-clinic`)

- Centered card layout
- Show list of user's clinics with last-accessed timestamp
- "Create New Clinic" CTA at bottom
- Search filter if user belongs to 5+ clinics
- Responsive: full-width cards on mobile

### 6.3 Patients (`/patients`)

**List View (default):**

| Viewport | Layout |
|----------|--------|
| Phone | Card list — each patient is a card with name, phone, status badge. Tap to expand/navigate |
| Tablet | Compact table — fewer columns (Name, Phone, Status, Actions) |
| Desktop | Full table — all columns (Name, DOB, Gender, Phone, Email, Blood Type, Last Visit, Status, Actions) |

**Features:**
- **Search** — debounced (300ms), search icon in input, clear button
- **Filters** — collapsible filter bar: Status (Active/Inactive), Gender, Blood Type, Date range
- **Sort** — clickable column headers (Name, DOB, Last Visit)
- **Pagination** — bottom of table, show "1–20 of 142 patients", page size selector (20/50/100)
- **Quick Actions** — row hover reveals: View, Edit, Deactivate
- **Bulk Actions** — checkbox selection, bulk deactivate/export
- **Add Patient** — FAB (floating action button) on mobile, top-right button on desktop
- **Patient Detail** — clicking a patient row navigates to `/patients/[id]` (new page, not drawer)

**Add/Edit Patient Form:**
- Full-page on mobile (navigate to `/patients/new` or `/patients/[id]/edit`)
- Side sheet on desktop (current behavior, but wider — `max-w-lg`)
- Form sections with clear headings: Personal Info → Contact → Medical
- Required fields marked with red asterisk
- Inline validation on blur
- Auto-save draft to localStorage (prevent data loss)

### 6.4 Patient Detail (`/patients/[id]`) — NEW PAGE

**Layout:**
- **Header:** Patient name, age, gender, status badge, avatar. Quick actions (Edit, Print, Deactivate)
- **Tabs or Sections:**

| Tab | Content |
|-----|---------|
| **Overview** | Summary card — demographics, contact, allergies (highlighted if present), last visit |
| **Background** | Medical/Surgical/Family/Social history + Medications + Immunizations (existing component, enhanced) |
| **Encounters** | List of past encounters for this patient, "New Encounter" button |
| **Medications** | Current and past prescriptions |
| **Documents** | Uploaded files (lab results, referrals, etc.) — future |
| **Timeline** | Chronological activity log — future |

**Responsive:**
- Tabs → scrollable horizontal list on mobile
- Header → stacks vertically on mobile (avatar above name)
- Action buttons → dropdown menu on mobile

### 6.5 Encounters (`/encounters`) — TO BUILD

**List View:**
- Table/card list of encounters across all patients
- Columns: Date, Patient Name, Doctor, Type (Follow-up/New/Emergency), Status (Scheduled/In Progress/Completed), Duration
- Filters: Date range, Doctor, Status, Type
- Today's encounters highlighted at top

**New Encounter Flow (`/encounters/new?patientId=X`):**
- **Step 1:** Patient selection (pre-filled if coming from patient detail) + encounter type + date/time
- **Step 2:** Chief complaint + vital signs (BP, temp, pulse, weight, height — auto-calculate BMI)
- **Step 3:** Examination notes (rich text or structured fields based on clinic preference)
- **Step 4:** Diagnosis (ICD-10 searchable combobox, multiple selections)
- **Step 5:** Prescriptions (drug search, dosage, frequency, duration — table format)
- **Step 6:** Lab orders (optional)
- **Step 7:** Review & finalize

**Responsive:**
- Stepper → vertical on mobile
- Vital signs → 2-column grid on tablet, 1-column on phone, 3-column on desktop
- Drug/diagnosis search → full-screen combobox on mobile

### 6.6 Medications (`/medications`) — TO BUILD

- Searchable drug database
- Current prescriptions across all patients
- Refill requests queue
- Drug interaction warnings

### 6.7 Settings (`/settings`) — TO BUILD

**Sections (tab or sidebar navigation):**

| Section | Content |
|---------|---------|
| **Clinic Profile** | Name, address, phone, logo upload, operating hours |
| **Staff Management** | Invite users, assign roles (Admin/Doctor/Nurse/Receptionist), manage permissions |
| **Preferences** | Default language, date format, currency, timezone |
| **Billing/Plan** | Current plan, usage metrics, upgrade CTA — future |
| **Integrations** | Lab system, pharmacy system, insurance — future |

---

## 7. Color System & Theming

### 7.1 Light Theme (default)

```
Background:      #FFFFFF (white)
Surface:         #F9FAFB (gray-50)
Primary:         #2563EB (blue-600) — actions, links, active states
Primary Hover:   #1D4ED8 (blue-700)
Success:         #059669 (emerald-600) — active, completed, saved
Warning:         #D97706 (amber-600) — pending, attention needed
Destructive:     #DC2626 (red-600) — errors, delete, critical alerts
Text Primary:    #111827 (gray-900)
Text Secondary:  #6B7280 (gray-500)
Border:          #E5E7EB (gray-200)
```

### 7.2 Dark Theme (optional, toggle in settings)

```
Background:      #0F172A (slate-900)
Surface:         #1E293B (slate-800)
Primary:         #3B82F6 (blue-500)
Text Primary:    #F1F5F9 (slate-100)
Text Secondary:  #94A3B8 (slate-400)
Border:          #334155 (slate-700)
```

### 7.3 Status Colors (consistent across all modules)

| Status | Color | Usage |
|--------|-------|-------|
| Active / Completed | Emerald | Patient active, encounter completed |
| Scheduled / Pending | Amber | Upcoming appointment, pending lab |
| In Progress | Blue | Encounter in progress |
| Cancelled / Inactive | Gray | Deactivated patient, cancelled appointment |
| Urgent / Critical | Red | Emergency encounter, drug allergy alert |

---

## 8. Typography

| Element | Size | Weight | Usage |
|---------|------|--------|-------|
| Page Title | `text-2xl` (24px) | Bold (700) | "Patients", "Encounters" |
| Section Heading | `text-lg` (18px) | Semibold (600) | Card titles, form sections |
| Body | `text-sm` (14px) | Normal (400) | Table cells, form labels, descriptions |
| Small/Caption | `text-xs` (12px) | Medium (500) | Badges, timestamps, helper text |
| Button | `text-sm` (14px) | Medium (500) | All button labels |

**Arabic adjustments:**
- Arabic text renders 1 size larger (e.g., body at `text-base` 16px instead of 14px)
- Font family: `"IBM Plex Sans Arabic"` for Arabic, `"Inter"` for English
- Line height increased by 0.25 for Arabic text blocks

---

## 9. Interaction Patterns

### 9.1 Loading States

- **Page load:** Full-page skeleton matching the layout structure
- **Table load:** Skeleton rows (5 rows of shimmer blocks)
- **Button action:** Spinner replaces button text, button disabled
- **Inline save:** "Saving..." indicator near the field (existing pattern — keep)
- **Navigation:** Top progress bar (NProgress or Next.js built-in)

### 9.2 Error States

- **Network error:** Full-width banner at top of content area with retry button
- **Empty table:** Illustration + "No patients found" + "Add your first patient" CTA
- **Form validation:** Inline error below each field, red border on input, summary at top of form
- **API error (500):** Toast notification with error message + "Contact support" link
- **Permission denied (403):** Toast with "You don't have permission to perform this action"

### 9.3 Success States

- **Record created:** Toast "Patient added successfully" + table auto-refreshes
- **Record updated:** Toast "Changes saved" (auto-dismiss 3s)
- **Record deleted:** Toast with undo option (5s window before permanent delete)

### 9.4 Navigation

- **Keyboard shortcuts:**
  - `⌘/Ctrl + K` — Global search (CommandMenu)
  - `⌘/Ctrl + N` — New patient (context-dependent)
  - `Esc` — Close any open modal/sheet/drawer
- **Breadcrumbs:** Shown on detail/edit pages: `Patients > Ahmed Al Rashid > Background`
- **Back navigation:** Browser back button always works correctly (no broken history states)

### 9.5 Touch Interactions (mobile/tablet)

- All tap targets minimum 44×44px (Apple HIG recommendation)
- Swipe-to-reveal actions on list items (Edit, Delete)
- Pull-to-refresh on list pages
- Long-press for context menu on table rows
- Pinch-to-zoom disabled on the app (viewport meta tag)

---

## 10. Accessibility Requirements

| Requirement | Standard | Implementation |
|-------------|----------|----------------|
| Color contrast | WCAG AA (4.5:1 text, 3:1 large text) | Verify all theme colors pass |
| Focus indicators | Visible focus ring on all interactive elements | Already via Radix + Tailwind `ring-*` |
| Keyboard navigation | Full keyboard operability | Tab order, Enter/Space activation, Esc to close |
| Screen reader | ARIA labels on all controls | Radix provides base; add labels for custom components |
| Skip links | "Skip to main content" link | Add to dashboard layout |
| Reduced motion | Respect `prefers-reduced-motion` | Disable transitions/animations when enabled |
| Form errors | Announced to screen readers | `aria-invalid` + `aria-describedby` on error fields |
| Live regions | Dynamic content updates announced | `aria-live="polite"` for toasts, save indicators |

---

## 11. Performance Targets

| Metric | Target | How |
|--------|--------|-----|
| First Contentful Paint | < 1.5s | Next.js SSR + code splitting |
| Largest Contentful Paint | < 2.5s | Optimize images, font loading |
| Time to Interactive | < 3.5s | Lazy-load below-fold components |
| Cumulative Layout Shift | < 0.1 | Skeleton loaders, fixed dimensions |
| Bundle size (JS) | < 200KB gzipped | Tree-shake, dynamic imports |
| API response display | < 500ms perceived | Optimistic updates via React Query |

---

## 12. Implementation Priority

### Phase 1 — Foundation (do first)
1. Responsive dashboard shell (collapsible sidebar, top bar, mobile nav)
2. i18n setup with `next-intl` (English + Arabic, RTL support)
3. Enhanced component library (Toast, DataTable, Card, Dialog, Skeleton, CommandMenu)
4. Color system standardization (light theme tokens finalized)
5. Typography system (Inter + IBM Plex Sans Arabic font loading)

### Phase 2 — Core Pages
6. Patient list page — responsive table/card view, filters, pagination, search
7. Patient detail page — tabbed layout with overview, background (migrate existing), encounters
8. Encounter list page — today's encounters, filters
9. New encounter flow — multi-step form with vitals, diagnosis, prescriptions

### Phase 3 — Polish
10. Dark mode support
11. Keyboard shortcuts (CommandMenu with ⌘K)
12. Settings page (clinic profile, staff, preferences)
13. Medications module
14. Loading/error/empty state polish across all pages
15. Touch interaction refinements (swipe, pull-to-refresh)

### Phase 4 — Advanced (future)
16. Offline support (PWA with service worker)
17. Push notifications (appointment reminders)
18. Document upload and viewer
19. Patient timeline view
20. Print-friendly encounter summaries
21. Dashboard analytics (patient count, encounter trends)

---

## 13. Technical Dependencies to Add

| Package | Purpose | Install |
|---------|---------|---------|
| `next-intl` | i18n with Next.js App Router | `npm install next-intl` |
| `sonner` | Toast notifications | `npm install sonner` |
| `cmdk` | Command menu (⌘K) | `npm install cmdk` |
| `@radix-ui/react-dropdown-menu` | Row action menus | `npx shadcn@latest add dropdown-menu` |
| `@radix-ui/react-select` | Select/combobox | `npx shadcn@latest add select` |
| `@radix-ui/react-popover` | Date picker, filter popovers | `npx shadcn@latest add popover` |
| `@radix-ui/react-avatar` | User/patient avatars | `npx shadcn@latest add avatar` |
| `@radix-ui/react-tooltip` | Icon-only button tooltips | `npx shadcn@latest add tooltip` |
| `@radix-ui/react-separator` | Visual dividers | `npx shadcn@latest add separator` |
| `@radix-ui/react-scroll-area` | Custom scrollbars | `npx shadcn@latest add scroll-area` |
| `date-fns` | Date formatting (locale-aware) | `npm install date-fns` |
| `nuqs` | URL search params state | `npm install nuqs` |

---

## 14. File Structure (proposed)

```
frontend/
├── messages/
│   ├── en.json                    # English translations
│   └── ar.json                    # Arabic translations
├── app/
│   ├── [locale]/                  # i18n route segment
│   │   ├── layout.tsx             # Locale-aware root layout
│   │   ├── page.tsx               # Landing
│   │   ├── (auth)/
│   │   │   ├── sign-in/[[...sign-in]]/page.tsx
│   │   │   └── sign-up/[[...sign-up]]/page.tsx
│   │   ├── select-clinic/page.tsx
│   │   └── (dashboard)/
│   │       ├── layout.tsx         # Responsive shell
│   │       ├── patients/
│   │       │   ├── page.tsx       # Patient list
│   │       │   └── [id]/
│   │       │       ├── page.tsx   # Patient detail
│   │       │       └── edit/page.tsx
│   │       ├── encounters/
│   │       │   ├── page.tsx       # Encounter list
│   │       │   └── new/page.tsx   # New encounter wizard
│   │       ├── medications/page.tsx
│   │       └── settings/
│   │           ├── page.tsx
│   │           ├── clinic/page.tsx
│   │           ├── staff/page.tsx
│   │           └── preferences/page.tsx
├── components/
│   ├── layout/
│   │   ├── app-sidebar.tsx        # Responsive sidebar
│   │   ├── top-bar.tsx            # Mobile/desktop top bar
│   │   ├── mobile-nav.tsx         # Sheet-based mobile nav
│   │   └── breadcrumbs.tsx
│   ├── patients/
│   │   ├── patient-table.tsx
│   │   ├── patient-card.tsx       # Mobile card view
│   │   ├── patient-form.tsx
│   │   ├── patient-header.tsx
│   │   └── patient-background-tab.tsx
│   ├── encounters/
│   │   ├── encounter-table.tsx
│   │   ├── encounter-wizard.tsx
│   │   ├── vitals-form.tsx
│   │   ├── diagnosis-search.tsx
│   │   └── prescription-table.tsx
│   ├── ui/                        # shadcn components (existing + new)
│   └── shared/
│       ├── command-menu.tsx
│       ├── data-table.tsx         # Generic sortable/filterable table
│       ├── empty-state.tsx
│       ├── error-boundary.tsx
│       ├── language-toggle.tsx
│       └── skeleton-loader.tsx
├── hooks/
│   ├── useCurrentUser.ts
│   ├── useMediaQuery.ts          # Responsive breakpoint hook
│   └── useDebounce.ts
├── types/
│   ├── user.types.ts
│   ├── patient.types.ts
│   └── encounter.types.ts
└── lib/
    ├── axios.ts
    ├── providers.tsx
    ├── utils.ts
    └── i18n.ts                    # next-intl configuration
```
