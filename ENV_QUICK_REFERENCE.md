# Environment Variables - Quick Reference Guide
## What Each App Needs

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CONCEPT 10 - ENV QUICK REFERENCE                 │
└─────────────────────────────────────────────────────────────────────┘

🔵 BACKEND (FastAPI - localhost:8000)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
File: .env

✅ REQUIRED:
  DATABASE_URL              → PostgreSQL connection
  SECRET_KEY                → JWT signing secret
  FRONTEND_ORIGINS          → CORS whitelist

❌ DOES NOT NEED:
  LANGSMITH_*               ✓ Removed (delegates to agentic service)
  OPENAI_API_KEY            ✓ Removed (delegates to agentic service)

Role: Handles user data, delegates AI to agentic service
Pattern: Backend → Agentic Service → OpenAI + LangSmith


🟢 FRONTEND (Next.js - localhost:3000)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
File: frontend/.env.local

✅ REQUIRED:
  NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY  → Client-side auth
  CLERK_SECRET_KEY                   → Server-side auth
  NEXT_PUBLIC_API_BASE_URL           → Backend API location
  NEXT_PUBLIC_CLERK_*                → Auth routing

❌ DOES NOT NEED (REMOVED FOR SECURITY):
  NEXT_PUBLIC_LANGSMITH_*           ✓ Removed (browser can't see)
  NEXT_PUBLIC_OPENAI_API_KEY        ✓ Removed (security risk)

Role: Browser UI only, never calls LLM APIs
Pattern: Frontend → Backend API (credentials hidden)


🟡 AGENTIC SERVICE (localhost:8001)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
File: concept10-agentic/.env

✅ REQUIRED:
  LANGCHAIN_API_KEY                 → LangSmith API key
  LANGCHAIN_TRACING_V2=true         → Enable tracing
  LANGCHAIN_ENDPOINT                → LangSmith endpoint
  LANGCHAIN_PROJECT                 → Project name
  OPENAI_API_KEY                    → LLM model access

❌ REMOVED (DUPLICATES):
  LANGSMITH_API_KEY                 ✓ Removed (use LANGCHAIN_API_KEY)
  LANGSMITH_PROJECT                 ✓ Removed (use LANGCHAIN_PROJECT)
  LANGSMITH_ENDPOINT                ✓ Removed (use LANGCHAIN_ENDPOINT)
  ENABLE_LANGSMITH                  ✓ Removed (use LANGCHAIN_TRACING_V2)

Role: Orchestrates AI agents, calls OpenAI, traces to LangSmith
Pattern: Only service holding LLM credentials


🟠 DASHBOARD (Vite - localhost:5173)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
File: concept10-agentic/dashboard/.env.local

✅ REQUIRED:
  VITE_API_BASE_URL                 → Agentic service API

❌ DOES NOT NEED:
  VITE_LANGSMITH_*                  ✓ Removed (UI only displays data)
  VITE_OPENAI_API_KEY               ✓ Removed (no LLM calls)

Role: Web UI for monitoring, never calls LLM APIs
Pattern: Dashboard → API calls only (read-only)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 CREDENTIAL DISTRIBUTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Credential              Backend  Frontend  Agentic  Dashboard
───────────────────────────────────────────────────────────────
CLERK_*                   -       ✅        -        -
DATABASE_URL              ✅      -         -        -
OPENAI_API_KEY            -       ✗         ✅       ✗
LANGCHAIN_*               -       ✗         ✅       ✗
LangSmith Tracing         -       ✗         ✅       ✗

Legend: ✅=Has it, ✗=Removed, -=Never needed


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔄 DATA FLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User Browser
    ↓
 Frontend (React/Next.js)
    │ ← Clerk auth (frontend/.env.local)
    ↓ REST API calls
 Backend (FastAPI)
    │ ← Database (DATABASE_URL)
    │
    ├→ User/Patient Data: Returns from DB
    │
    ├→ AI Request: Calls Agentic Service
    │
    └→ Agentic Service (concept10-agentic)
        ├ LANGCHAIN_API_KEY → LangSmith (traces)
        ├ OPENAI_API_KEY → OpenAI (gpt-4o)
        └ Returns: AI result + metadata

Dashboard
    ↓
    Agentic Service API (monitoring only)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ VALIDATION SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[✓] Backend - Only needed variables
[✓] Frontend - REMOVED sensitive keys to prevent browser exposure
[✓] Agentic - Kept actual credentials (LANGCHAIN_*, OPENAI_API_KEY)
[✓] Dashboard - Only API URL (read-only UI)
[✓] Removed 24 duplicate/unused variables
[✓] No security vulnerabilities
[✓] Clean separation of concerns
```

---

## Answer to Your Questions

**Q: Does Frontend need LangSmith and OpenAI keys?**
> ❌ **NO**. Frontend is a SPA running in the browser. It never makes LLM calls or traces. Exposing these keys in environment variables is a security risk.

**Q: Does Backend need LangSmith and OpenAI keys?**
> ❌ **NO**. Backend is an API that delegates AI work to the Agentic Service. Backend should only handle user data and auth.

**Q: Which app needs them?**
> ✅ **ONLY Agentic Service**. It's the specialized service that orchestrates agents and calls OpenAI models.

---

## Files Status

| File | Status | Variables | Change |
|------|--------|-----------|--------|
| `.env` | ✅ | 9 | -5 removed |
| `frontend/.env.local` | ✅ | 8 | -10 removed |
| `concept10-agentic/.env` | ✅ | 46 | -4 removed (duplicates) |
| `concept10-agentic/dashboard/.env.local` | ✅ | 1 | -5 removed |
| **TOTAL** | **✅** | **64** | **-24 removed** |

---

**Validation Date:** March 12, 2026
