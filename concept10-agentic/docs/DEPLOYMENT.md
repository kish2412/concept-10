# Deployment

## Scope

This guide covers deploying:

- Backend FastAPI service (`api.main:app`)
- Dashboard Vite app (`dashboard/`)

## Deployment Strategy

Recommended environments:

- `local`: developer machine
- `dev`: shared preview/staging
- `prod`: production

Use separate env vars per environment, especially for:

- `LANGCHAIN_API_KEY`
- `OTEL_EXPORTER_OTLP_ENDPOINT`
- `CONTEXT_REDIS_URL`
- `VITE_API_BASE_URL`

## Backend Deployment

### Build

Install dependencies and run checks:

```bash
pip install -e ".[core,dev,observability,governance]"
pytest
ruff check .
mypy .
```

### Run Command

```bash
uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### Required Runtime Validation

After deploy:

1. `GET /health` returns `200` and `{ "status": "ok" }`.
2. `GET /agents` returns registry data.
3. Execute one `/orchestrate/{agent_id}` request successfully.

## Dashboard Deployment

### Build

```bash
cd dashboard
npm ci
npm run build
```

### Runtime Config

Set `VITE_API_BASE_URL` to deployed backend base URL.

Example:

```env
VITE_API_BASE_URL=https://your-backend.example.com
```

### Validation

1. Graph loads from `/agents/graph`.
2. Agent detail panel loads `/agents/{agent_id}`.
3. Active request list handles empty/non-empty response safely.

## Release Checklist

1. Backend tests pass.
2. Dashboard build passes.
3. `.env` values reviewed for target environment.
4. Health check verified post-deploy.
5. Tracing/logging validated with one smoke request.

## Notes

- This repository currently does not include finalized CI/CD workflows under `.github/workflows/`.
- If you add workflows, keep backend and dashboard deploy jobs independent and block deploy on test/lint failures.
