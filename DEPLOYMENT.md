# Deployment

This guide aligns with the current GitHub workflows and supports dev and prod environments.

## Workflows

- CI: `.github/workflows/ci.yml` (runs on PRs)
- Dev deploy: `.github/workflows/deploy-dev.yml` (push to `dev`)
- Prod deploy: `.github/workflows/deploy-prod.yml` (push to `main`)
- Manual fallback: `.github/workflows/cd.yml` (workflow_dispatch only)

## Targets

### Dev

- Frontend: Vercel preview
- Backend: Railway dev service
- Database: Railway dev DB

### Prod

- Frontend: Vercel production
- Backend: Railway prod service
- Database: Railway prod DB

## Required Secrets and Vars

From workflows:

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`
- `RAILWAY_TOKEN`
- `DEV_BACKEND_URL`
- `PROD_BACKEND_URL`
- `DEV_DATABASE_URL`
- `PROD_DATABASE_URL`
- `CLERK_SECRET_KEY` (CI build)

Repo variables:

- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`

## Deploy Dev (push to `dev`)

`deploy-dev.yml` pipeline:

1. Lint + test frontend
2. Lint + test backend
3. Deploy frontend preview (Vercel CLI)
4. Deploy backend dev (Railway CLI)
5. Run Alembic migrations on dev DB
6. Health check backend

## Deploy Prod (push to `main`)

`deploy-prod.yml` pipeline:

1. Lint + test frontend
2. Lint + test backend
3. Deploy frontend production (Vercel CLI)
4. Deploy backend prod (Railway CLI)
5. Run Alembic migrations on prod DB
6. Health check backend

## Manual Fallback CD

`cd.yml` runs only via manual trigger. It:

1. Runs migrations with `PRODUCTION_DATABASE_URL`
2. Triggers Railway deploy hook
3. Triggers Vercel deploy hook
4. Runs smoke tests

Only use this if the normal deploy workflows are blocked.

## Optional: Supabase Database

If you use Supabase for production DB (as per earlier guidance), convert the connection string to async SQLAlchemy format:

```
postgresql+asyncpg://postgres.<project_ref>:<password>@<host>:5432/postgres?ssl=require
```

Use the same DSN in Railway `DATABASE_URL` and GitHub `PROD_DATABASE_URL`.
