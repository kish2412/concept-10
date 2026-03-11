# agent-orchestration-framework

Async-first Python monorepo scaffold for an AI Agentic Orchestration Framework.

## Structure

```text
concept10-agentic/
├── agents/
│   ├── registry/
│   ├── orchestrator/
│   ├── utility/
│   └── specialist/
├── core/
│   ├── context/
│   ├── graph/
│   ├── prompts/
│   ├── schemas/
│   └── governance/
├── observability/
├── api/
├── dashboard/
├── tests/
├── .github/copilot/
├── pyproject.toml
├── .env.example
└── README.md
```

## Principles

- Python `3.11+`
- Async-first (`asyncio`) runtime and interfaces
- Environment-based configuration only (`python-dotenv` + `pydantic-settings`)
- No hardcoded secrets or model names in source

## Quick Start

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\\Scripts\\Activate.ps1
pip install -e ".[core,dev,observability,governance]"
cp .env.example .env
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## Run Agentic API + Dashboard

Backend:

```bash
uvicorn api.app:app --reload --host 0.0.0.0 --port 8001
```

Dashboard:

```bash
cd dashboard
npm install
npm run dev
```

## Triage Specialist Endpoint

- `POST /specialist/triage/summarise`
- Requires `Authorization: Bearer <token>` header
- Requires `X-User-Role` in: `nurse`, `reception`, `doctor`, `admin`

## Observability and Guardrails Checks

1. Ensure `LANGCHAIN_TRACING_V2=true` and LangSmith API settings are present in `.env`.
2. Submit a triage request and verify response headers include `X-Trace-ID` and optionally `X-LangSmith-URL`.
3. Confirm guardrails are active with `ENABLE_GOVERNANCE_VALIDATION=true`.
4. Review governance events in `core/governance/governance_audit.jsonl`.

## Dependency Groups

- `core`: FastAPI, schema/config, prompting, agent graph runtime
- `dev`: test, lint, type-check tooling
- `observability`: LangSmith and OpenTelemetry
- `governance`: Guardrails AI validation

## Next Implementation Steps

1. Define agent contracts and registration schema in `agents/registry/agent_registry.yaml`.
2. Implement graph state and transitions under `core/graph/`.
3. Add category routers under `api/routers/`.
4. Wire tracing in `observability/`.
5. Scaffold dashboard views and React Flow graph in `dashboard/`.
