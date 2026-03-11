# Agent Orchestration Dashboard

React + Vite operations dashboard for agent registry visibility, orchestration requests, and trace drill-down.

## Local Start

```bash
npm install
npm run dev
```

Default URL: `http://localhost:5173`

## Environment

Create `.env` in this folder:

```env
VITE_API_BASE_URL=http://localhost:8001
```

Point this value to the running concept10-agentic API.

## What to Verify

1. Agent graph renders and includes specialist agents.
2. Request drawer shows orchestration metadata and trace links.
3. LangSmith links open when backend sends `X-LangSmith-URL`.
4. Guardrail/governance events are reflected in API results and audit logs.
