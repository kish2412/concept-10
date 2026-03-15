# Local Setup

This guide is the single source of truth for running the full stack locally.

## 1) Prerequisites

Install:

- Git
- Python 3.11+
- PostgreSQL 15+
- Node.js LTS (npm)

Verify:

```powershell
git --version
python --version
node --version
npm --version
psql --version
```

## 2) Clone and enter the repo

```powershell
git clone <your-repo-url>
Set-Location concept-10
```

## 3) Backend (FastAPI)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with your local values (see `ENVIRONMENT.md`).

Create local database:

```sql
CREATE DATABASE clinic_saas;
```

Run migrations and start API:

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

Backend URL: `http://localhost:8000`

## 4) Frontend (Next.js)

```powershell
Set-Location frontend
npm.cmd install
Copy-Item .env.example .env.local
```

Fill in Clerk keys in `frontend/.env.local` (see `ENVIRONMENT.md`).

Start dev server:

```powershell
npm.cmd run dev
```

Frontend URL: `http://localhost:3000`

## 5) Agentic Service (optional but used by AI features)

```powershell
Set-Location ..\concept10-agentic
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[core,dev,observability,governance]"
Copy-Item .env.example .env
```

Update `concept10-agentic/.env` with LangSmith/OpenAI keys (see `ENVIRONMENT.md`).

Start agentic API:

```powershell
uvicorn api.app:app --reload --host 0.0.0.0 --port 8001
```

Agentic URL: `http://localhost:8001`

## 6) Agentic Dashboard (optional)

```powershell
Set-Location dashboard
npm.cmd install
Copy-Item .env.example .env.local
```

Set `VITE_API_BASE_URL=http://localhost:8001` in `dashboard/.env.local`.

Start dashboard:

```powershell
npm.cmd run dev
```

Dashboard URL: `http://localhost:5173`

## 7) Validation Checklist

- Backend running on `http://localhost:8000`
- Frontend running on `http://localhost:3000`
- Agentic service running on `http://localhost:8001`
- Dashboard running on `http://localhost:5173`
- Clerk sign-in works and routes load: `/patients`, `/encounters`, `/medications`, `/settings`
- Triage summary generation succeeds in an encounter

## Troubleshooting (Windows)

### A) `npm` is not recognized

- Use `npm.cmd` instead of `npm`, or
- Ensure `C:\Program Files\nodejs` is on PATH, then reopen PowerShell.

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
