# Concept 10

Multi-tenant outpatient management system (FastAPI + Next.js) with an optional agentic service for AI-assisted workflows.

## Repo Layout

- Backend (FastAPI): `concept-10/app/`
- Frontend (Next.js): `concept-10/frontend/`
- Agentic service: `concept-10/concept10-agentic/`
- Agentic dashboard: `concept-10/concept10-agentic/dashboard/`

## Ports (Local)

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- Agentic service: `http://localhost:8001`
- Agentic dashboard: `http://localhost:5173`

## Start Here

- Local setup: `concept-10/SETUP.md`
- Environment variables: `concept-10/ENVIRONMENT.md`
- Deployment: `concept-10/DEPLOYMENT.md`
- Product/UI requirements: `concept-10/PRODUCT_UI.md`

## Quick Health Checks

- Backend: `GET http://localhost:8000/health` -> `{ "status": "ok" }`
- Agentic service: `GET http://localhost:8001/health` -> `{ "status": "ok" }`
- Specialist ping: `GET http://localhost:8001/specialist/ping` -> `{ "status": "specialist_ok" }`
