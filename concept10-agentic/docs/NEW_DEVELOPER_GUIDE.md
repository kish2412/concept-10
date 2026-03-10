# New Developer Guide

## Purpose

Welcome to `concept10-agentic`, an async-first agent orchestration framework with:

- FastAPI backend (`api/`)
- Agent registry and contracts (`agents/`)
- Core orchestration/runtime modules (`core/`)
- Observability integrations (`observability/`)
- React dashboard (`dashboard/`)

## Architecture at a Glance

- `agents/registry/agent_registry.yaml`
  - Source of truth for configured agents.
- `agents/registry/loader.py`
  - Loads and validates agent definitions and referenced schemas/templates.
- `core/graph/`
  - Builds and executes orchestration graphs.
- `core/context/`
  - Session/context storage and token-aware context handling.
- `core/governance/`
  - Governance validation and rail profiles.
- `api/app.py`
  - FastAPI app, middleware, router wiring, and `GET /health`.
- `dashboard/`
  - Vite + React graph/ops UI.

## Runtime Flow

1. FastAPI starts from `api.main:app` (re-export of `api.app:app`).
2. App lifespan loads `AgentRegistry` and initializes `GraphExecutor`.
3. Request middleware sets `X-Request-ID` and tracing context.
4. `/orchestrate/{agent_id}` validates input and executes the graph.
5. Dashboard consumes `/agents/*` and `/orchestrate/*` endpoints.

## Key Endpoints

- `GET /health`
- `GET /agents`
- `GET /agents/{agent_id}`
- `GET /agents/graph`
- `POST /orchestrate/{agent_id}`
- `POST /orchestrate/{agent_id}/stream`
- `GET /orchestrate/{agent_id}/status/{request_id}`
- `POST /orchestrate/{agent_id}/approve/{request_id}`

## Day 1 Checklist

1. Read `README.md` and `docs/PROJECT_SETUP.md`.
2. Run backend and confirm `GET /health` returns `{ "status": "ok" }`.
3. Start dashboard and verify agent graph renders.
4. Inspect `agents/registry/agent_registry.yaml` to understand active agents.
5. Run tests before making changes.

## Coding Conventions

- Keep source code async-first for backend workflows.
- Use env-driven configuration; do not hardcode secrets.
- Keep registry entries semver-compliant.
- Add tests for API or graph changes in `tests/`.
- Preserve request-tracing context through new execution paths.
