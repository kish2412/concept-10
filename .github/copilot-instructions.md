# GitHub Copilot Instructions

## Project Stack
- **Frontend**: React/Next.js (deployed to Vercel)
- **Backend**: Python / FastAPI (deployed to Railway)
- **Database**: PostgreSQL

## Workspace Path Mapping
- This repository does not use a `backend/` folder.
- Backend code lives at repo root (`app/`, `alembic/`, `requirements.txt`, `.env.example`).
- Any reference below to `backend/...` should map to the repo root equivalent.

## Environment Map

| Environment | Frontend         | Backend               | Database              |
|-------------|------------------|-----------------------|-----------------------|
| **Local**   | localhost:3000   | localhost:8000        | localhost:5432        |
| **Dev**     | Vercel (preview) | Railway dev service   | Railway dev DB        |
| **Prod**    | Vercel (prod)    | Railway prod service  | Railway prod DB       |

> Local DB is **only** for local runs. Dev and Prod both use Railway-hosted databases.

---

## 1. Dependency Checks

### Frontend (React)
- Every `import` must have a matching entry in `frontend/package.json`
- Dev-only tools (eslint, vitest, types) go in `devDependencies`, not `dependencies`
- Lock file (`package-lock.json` / `yarn.lock` / `pnpm-lock.yaml`) must be committed and in sync
- When adding a package, remind: `cd frontend && npm install`

### Backend (FastAPI / Python)
- Every `import` must have a matching entry in `requirements.txt` (or `pyproject.toml`)
- Pin all versions - no unpinned `package>=x` entries in production requirements
- Separate dev deps into `requirements-dev.txt` (pytest, black, ruff, mypy, etc.)
- When adding a package, remind: `pip install -r requirements.txt`
- Always verify these core packages are present: `fastapi`, `uvicorn[standard]`, `pydantic`, `python-dotenv`, and `alembic` if SQLAlchemy models exist

---

## 2. Environment Variable Rules

### Structure
Every env var used anywhere in code must appear in both:
1. `frontend/.env.example` - for frontend vars
2. `.env.example` - for FastAPI vars

### `frontend/.env.example`
```env
# LOCAL (.env.local - never commit actual values)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1

# DEV (set in Vercel -> Settings -> Environment Variables -> Preview)
# NEXT_PUBLIC_API_BASE_URL=https://your-backend-dev.railway.app/api/v1

# PROD (set in Vercel -> Settings -> Environment Variables -> Production)
# NEXT_PUBLIC_API_BASE_URL=https://your-backend.railway.app/api/v1
```

### `.env.example`
```env
# LOCAL (.env - never commit actual values)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/clinic_saas
SECRET_KEY=local_dev_secret_change_me
FRONTEND_ORIGINS=["http://localhost:3000"]
ENVIRONMENT=local

# DEV (set in Railway dev service -> Variables)
# DATABASE_URL=postgresql://railway:xxx@xxx.railway.internal:5432/railway
# SECRET_KEY=<generate a strong secret>
# FRONTEND_ORIGINS=["https://your-app-git-dev.vercel.app"]
# ENVIRONMENT=dev

# PROD (set in Railway prod service -> Variables)
# DATABASE_URL=postgresql://railway:xxx@xxx.railway.internal:5432/railway
# SECRET_KEY=<generate a strong secret>
# FRONTEND_ORIGINS=["https://your-app.vercel.app"]
# ENVIRONMENT=prod
```

### Rules Copilot must always follow
- Never hardcode secrets, URLs, or DB connection strings in source code
- Never reference a Railway or Vercel URL inside a local `.env` - flag as misconfiguration
- `DATABASE_URL` in local `.env` must always point to `localhost`
- FastAPI CORS must read origins from env vars, not be hardcoded
- Frontend API base URL must come from env vars, never hardcoded

---

## 3. FastAPI-Specific Rules

When generating or modifying FastAPI code:
- Load all config via `pydantic-settings` (`BaseSettings`) - never raw `os.environ` access without validation
- CORS middleware must use env-provided origins (`FRONTEND_ORIGINS` in this repo)
- Always check that `alembic` is initialized if SQLAlchemy models exist - if not, suggest running `alembic init`
- Health check endpoint (`GET /health`) should exist and return `{"status": "ok"}`
- Never import from `app` or `main` in a circular way - use dependency injection

---

## 4. Branching & Deployment Strategy

```text
feature/* or fix/*
       |
       v
    dev branch  --push-->  DEV environment
                              Frontend: Vercel preview deployment
                              Backend:  Railway dev service
                              Database: Railway DEV DB  <- not localhost
       |
    Pull Request + merge
       |
       v
   main branch  --push-->  PROD environment
                              Frontend: Vercel production deployment
                              Backend:  Railway prod service
                              Database: Railway PROD DB

[Local machine - never deployed]
   Frontend: localhost:3000
   Backend:  localhost:8000
   Database: localhost:5432  <- local only
```

---

## 5. CI/CD Workflows

### `.github/workflows/deploy-dev.yml`
- Trigger: `push` to `dev`
- Jobs: lint frontend -> test frontend -> lint backend -> test backend -> deploy Vercel preview -> deploy Railway dev -> run `alembic upgrade head` with `DEV_DATABASE_URL`

### `.github/workflows/deploy-prod.yml`
- Trigger: `push` to `main`
- Jobs: lint frontend -> test frontend -> lint backend -> test backend -> deploy Vercel production -> deploy Railway prod -> run `alembic upgrade head` with `PROD_DATABASE_URL`

---

## 6. Required GitHub Secrets

| Secret Name         | Used In   | Description                              |
|---------------------|-----------|------------------------------------------|
| `VERCEL_TOKEN`      | Both      | Vercel personal access token             |
| `VERCEL_ORG_ID`     | Both      | Vercel org/team ID                       |
| `VERCEL_PROJECT_ID` | Both      | Vercel project ID                        |
| `RAILWAY_TOKEN`     | Both      | Railway API token                        |
| `DEV_BACKEND_URL`   | Dev only  | Railway dev backend public URL           |
| `PROD_BACKEND_URL`  | Prod only | Railway prod backend public URL          |
| `DEV_DATABASE_URL`  | Dev only  | Railway dev PostgreSQL connection string |
| `PROD_DATABASE_URL` | Prod only | Railway prod PostgreSQL connection string|

---

## 7. Ongoing Code Generation Rules

| Scenario                             | Copilot must...                                                          |
|--------------------------------------|--------------------------------------------------------------------------|
| New Python `import` added            | Check `requirements.txt` and add pinned version if missing              |
| New npm import added                 | Check `frontend/package.json` and add to correct dependency section      |
| New settings/env var used            | Add to `.env.example` with placeholder + comment                         |
| New frontend env var used            | Add to `frontend/.env.example` with placeholder + comment                |
| SQLAlchemy model created or changed  | Remind to run `alembic revision --autogenerate` and commit migration     |
| New API route added                  | Confirm registered in FastAPI router and CORS not hardcoded              |
| Hardcoded URL found in source        | Replace with env var and add to env example                              |
| Workflow trigger modified            | Validate it matches `dev` -> dev env and `main` -> prod env only         |
| New service added to stack           | Update Docker docs/config and both `.env.example` files                  |
