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
