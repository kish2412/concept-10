# MVP Deployment (Option 1): Supabase + Railway + Vercel

This guide matches the current GitHub Actions workflows in `.github/workflows`.

## Architecture

- Database: Supabase Postgres
- Backend (`app/` FastAPI): Railway using the root `Dockerfile`
- Frontend (`frontend/` Next.js): Vercel
- Migrations: GitHub Actions runs `alembic upgrade head` before deploy hooks

## 1) Supabase setup (production database)

1. Create a Supabase project.
2. In Supabase, open **Project Settings -> Database -> Connection string**.
3. Copy a Postgres URI and convert to async SQLAlchemy format for this project:
   - Start with Supabase URI
   - Replace prefix with `postgresql+asyncpg://`
4. Ensure SSL is enabled in the connection URL (commonly `?ssl=require`).
5. Save this value as your production app/migration DSN.

Example shape:

```text
postgresql+asyncpg://postgres.<project_ref>:<password>@<host>:5432/postgres?ssl=require
```

Notes:

- If your password contains special characters, URL-encode it.
- Use the same DSN format for both Railway `DATABASE_URL` and GitHub `PRODUCTION_DATABASE_URL`.

## 2) Railway setup (FastAPI backend)

1. Create a Railway project.
2. Add a service from your GitHub repo.
3. Set service root to repository root so Railway uses the existing root `Dockerfile`.
4. Add backend environment variables in Railway:
   - `ENVIRONMENT=production`
   - `API_V1_PREFIX=/api/v1`
   - `DATABASE_URL=<Supabase asyncpg URL>`
   - `SECRET_KEY=<strong random value>`
   - `FRONTEND_ORIGINS=https://<your-vercel-domain>`
5. Deploy once manually to confirm startup.
6. Capture backend public URL (used by Vercel + smoke test), e.g.:
   - `https://<railway-backend-domain>/openapi.json`

## 3) Vercel setup (Next.js frontend)

1. Import the same GitHub repository in Vercel.
2. Set **Root Directory** to `frontend`.
3. Set production environment variables:
   - `NEXT_PUBLIC_API_BASE_URL=https://<railway-backend-domain>/api/v1`
   - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=<pk_...>`
   - `CLERK_SECRET_KEY=<sk_...>`
   - `NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in`
   - `NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up`
4. Trigger a first deploy and verify frontend loads.

## 4) GitHub Actions configuration

In GitHub repo: **Settings -> Secrets and variables -> Actions**.

### Repository secrets

- `PRODUCTION_DATABASE_URL`
  - Supabase asyncpg DSN used by CD migration step.
- `RAILWAY_DEPLOY_HOOK_URL`
  - Railway deploy hook for backend service.
- `VERCEL_DEPLOY_HOOK_URL`
  - Vercel deploy hook for production deploy.
- `CLERK_SECRET_KEY`
  - Used by frontend CI build.
- `BACKEND_HEALTHCHECK_URL`
  - Example: `https://<railway-backend-domain>/openapi.json`
- `FRONTEND_URL`
  - Example: `https://<your-vercel-domain>`

### Repository variables

- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`

## 5) Deploy flow from GitHub

1. Push feature branch and open PR.
2. `CI` workflow runs (`.github/workflows/ci.yml`):
   - backend compile/import checks
   - frontend lint/build
3. Merge PR into `main`.
4. `CD` workflow runs (`.github/workflows/cd.yml`):
   1. run Alembic migrations against Supabase (`PRODUCTION_DATABASE_URL`)
   2. trigger Railway deploy hook
   3. trigger Vercel deploy hook
   4. run smoke checks on backend + frontend URLs

## 6) Recommended branch protection

For `main`, require:

- `CI / Backend checks`
- `CI / Frontend checks`

This ensures only validated changes reach production CD.

## 7) Verification checklist

- Railway backend `/openapi.json` returns HTTP 200.
- Vercel frontend homepage returns HTTP 200.
- Login works and protected pages load data from backend.
- New schema changes appear after merge to `main` (migration step success).

## 8) Rollback guidance

- Backend: redeploy previous successful Railway revision.
- Frontend: promote previous Vercel deployment.
- Database: prefer forward-fix migration; avoid emergency down-migrations unless tested.
