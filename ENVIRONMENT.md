# Environment Variables

This file defines the authoritative env vars for each app. Do not commit real secrets.

## Principles

- Frontend and dashboard must never contain LLM or tracing credentials.
- Backend delegates AI to the agentic service; it does not need LLM keys.
- Agentic service is the only component that holds LLM and LangSmith keys.

## Backend (`.env` at repo root)

Required:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/clinic_saas
SECRET_KEY=replace_with_secure_random_string
FRONTEND_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```

Agentic integration:

```
AGENTIC_ENABLED=true
AGENTIC_SERVICE_BASE_URL=http://localhost:8001
AGENTIC_SERVICE_TOKEN=replace_with_local_service_token
AGENTIC_SERVICE_ROLE=nurse
AGENTIC_SERVICE_TIMEOUT_SECONDS=20
```

Optional LLM fallback (only if you enable it in backend code):

```
LLM_PROVIDER=none
LLM_MODEL=none
OPENAI_API_KEY=
OPENAI_BASE_URL=
```

## Frontend (`frontend/.env.local`)

Required:

```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your_clerk_publishable_key
CLERK_SECRET_KEY=sk_test_your_clerk_secret_key
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/patients
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/select-clinic
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Do not add `OPENAI_API_KEY`, `LANGCHAIN_*`, or `LANGSMITH_*` here.

## Agentic Service (`concept10-agentic/.env`)

Required for tracing + LLM:

```
LANGCHAIN_API_KEY=lsv2_...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_PROJECT=concept10-dev
OPENAI_API_KEY=sk-...
DEFAULT_AGENT_PROVIDER=openai
DEFAULT_AGENT_MODEL=gpt-4o
```

Core runtime:

```
API_HOST=0.0.0.0
API_PORT=8001
API_PREFIX=/api/v1
AGENT_REGISTRY_PATH=agents/registry/agent_registry.yaml
ORCHESTRATION_TIMEOUT_SECONDS=60
CONTEXT_BACKEND=memory
CONTEXT_REDIS_URL=redis://localhost:6379/0
```

Notes:

- The API does not currently mount routes under `API_PREFIX`, so the dashboard should target the base URL without `/api/v1`.
- If you enable Redis, ensure the service is running: `redis-cli ping` -> `PONG`.

## Agentic Dashboard (`concept10-agentic/dashboard/.env.local`)

Required:

```
VITE_API_BASE_URL=http://localhost:8001
```

No other keys are required.

## Clerk Setup

1. Create an app in the Clerk dashboard named "Concept 10".
2. Enable Organizations.
3. Copy publishable and secret keys into `frontend/.env.local`.

## Secrets Hygiene

- Never commit `.env` or `.env.local` files.
- Rotate any keys that were ever committed to docs or config.
