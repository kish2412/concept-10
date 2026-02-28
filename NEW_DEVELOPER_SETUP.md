# Concept 10 - New Developer Setup Guide

This document explains how to set up the full project (backend + frontend) on a brand-new computer.

## 1) Prerequisites

Install these tools first:

- Git
- Python 3.11+
- PostgreSQL 15+
- Node.js LTS (includes npm)

### Verify installations

Open PowerShell and run:

```powershell
git --version
python --version
node --version
npm --version
psql --version
```

If `npm` or `node` is not recognized on Windows:

```powershell
winget install --id OpenJS.NodeJS.LTS -e
```

Then close and reopen PowerShell.

---

## 2) Clone repository

```powershell
git clone <your-repo-url> "Concept 10 - New Project"
Set-Location "Concept 10 - New Project"
```

---

## 3) Backend setup (FastAPI)

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

### Configure backend environment

Edit `.env` with your local values:

- `DATABASE_URL=postgresql+asyncpg://<user>:<password>@localhost:5432/clinic_saas`
- `SECRET_KEY=<long-random-secret>`
- `FRONTEND_ORIGINS=http://localhost:3000,http://127.0.0.1:3000`

### Create local PostgreSQL database

```sql
CREATE DATABASE clinic_saas;
```

### Run migrations

```powershell
alembic revision --autogenerate -m "init"
alembic upgrade head
```

### Run backend

```powershell
uvicorn app.main:app --reload
```

Backend URL: `http://localhost:8000`

---

## 4) Frontend setup (Next.js)

Open a new terminal and run:

```powershell
Set-Location "<path-to>\Concept 10 - New Project\frontend"
npm.cmd install
Copy-Item .env.local.example .env.local
```

### Configure Clerk (required)

1. Create/claim app in Clerk dashboard.
2. Use app name: `Concept 10`.
3. Enable Organizations (used as clinic/tenant context).
4. Copy API keys to `frontend/.env.local`:

```dotenv
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...
CLERK_SECRET_KEY=sk_...
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

### Run frontend

```powershell
npm.cmd run dev
```

Frontend URL: `http://localhost:3000`

---

## 5) Daily development workflow

### Terminal A (backend)

```powershell
Set-Location "<path-to>\Concept 10 - New Project"
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

### Terminal B (frontend)

```powershell
Set-Location "<path-to>\Concept 10 - New Project\frontend"
npm.cmd run dev
```

---

## 6) Troubleshooting (Windows)

### A) `npm` is not recognized

- Use `npm.cmd` instead of `npm`, or
- Ensure `C:\Program Files\nodejs` is on PATH, then reopen terminal.

### B) PowerShell parser error when using quoted command path

Wrong:

```powershell
"C:\Program Files\nodejs\npm.cmd" run dev
```

Correct:

```powershell
& "C:\Program Files\nodejs\npm.cmd" run dev
```

### C) `next dev` says `'node' is not recognized`

Node path is missing in current session:

```powershell
$env:Path = "C:\Program Files\nodejs;$env:Path"
node -v
npm -v
```

### D) Script policy blocks npm (`npm.ps1` not signed)

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Or continue using `npm.cmd`.

---

## 7) First-time validation checklist

- Backend starts at `http://localhost:8000`
- Frontend starts at `http://localhost:3000`
- Clerk sign-in page opens
- After sign-in + org selection, dashboard routes load:
  - `/patients`
  - `/encounters`
  - `/medications`
  - `/settings`
