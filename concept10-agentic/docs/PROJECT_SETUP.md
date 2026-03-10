# Project Setup

## Prerequisites

- Python `3.11+`
- Node.js `18+` (for `dashboard/`)
- Git

Optional:

- Redis (if `CONTEXT_BACKEND=redis`)
- LangSmith and OTEL endpoints for tracing

## 1. Clone and Enter Project

```bash
git clone <repo-url>
cd concept10-agentic
```

## 2. Backend Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -e ".[core,dev,observability,governance]"
```

Create local env file:

```bash
cp .env.example .env
```

Windows alternative:

```powershell
Copy-Item .env.example .env
```

Start backend:

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## 3. Dashboard Setup

```bash
cd dashboard
npm install
```

Create dashboard env:

```bash
cp .env.example .env
```

The current dashboard defaults to backend root routes (no API prefix in app router wiring). Keep:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Start dashboard:

```bash
npm run dev
```

Build verification:

```bash
npm run build
```

## 4. Quality Checks

From `concept10-agentic/`:

```bash
pytest
ruff check .
mypy .
```

## 5. Common Issues

- `404` from dashboard API calls:
  - Check `VITE_API_BASE_URL` matches backend route prefix actually used by `api/app.py`.
- Tracing not visible:
  - Ensure LangSmith/OTEL env vars are set and enabled (`LANGCHAIN_TRACING_V2`, `ENABLE_OTEL`).
- Context failures with Redis:
  - Verify `CONTEXT_REDIS_URL` and that Redis is reachable.
