# Agentic Implementation Audit & Improvement Plan

Date: 2026-03-08
Scope: Full workspace review (`app/`, `frontend/`, `tests/`, `.github/workflows/`, env/config files)

## Executive Summary
Overall agentic maturity is **4.5/10**. The codebase has a strong foundation for AI-assisted clinical features (typed schemas, tenant-aware gating, role checks, and multiple specialized agent endpoints), but it is missing several production-critical controls: centralized prompt/tool orchestration, robust retry/timeout logic, explicit HITL checkpoints, cost/latency budgets, and dedicated agent evaluation tests.

A critical security issue was identified: **a real-looking OpenAI API key appears in `.env.example`**.

---

## Step 1 - Audit Checklist

| # | Principle | Status | Evidence (file:line) | Gap Summary |
|---|---|---|---|---|
| 1 | Separate Input/Output Schema Structure | ✅ Implemented | `app/schemas/encounter.py:425`, `app/schemas/encounter.py:429`, `app/schemas/encounter.py:446` | Distinct request/response models for AI routes are present. |
| 2 | Structured System Prompt Maintenance | ⚠️ Partial | `app/services/agentic_clinical_agents_service.py:77`, `app/services/agentic_clinical_agents_service.py:78` | Prompt is hardcoded inline; no versioned prompt registry/templates. |
| 3 | Memory Management (short/long-term) | ⚠️ Partial | `app/services/agentic_clinical_agents_service.py:90`, `app/services/agentic_clinical_agents_service.py:114` | Context is fetched ad hoc (`limit(5)`), but no persistent memory strategy exists. |
| 4 | Tool/Function Registry | ❌ Missing | `app/api/v1/routes/encounters.py:264`, `app/api/v1/routes/encounters.py:287`, `app/api/v1/routes/encounters.py:310` | Direct per-route function calls; no centralized registry/dispatcher. |
| 5 | State Machine / Workflow Orchestration | ⚠️ Partial | `app/services/encounter_service.py:496`, `app/services/encounter_service.py:505` | Encounter status exists, but no explicit multi-step agent workflow state machine. |
| 6 | Error Handling & Retry Logic | ⚠️ Partial | `app/services/agentic_clinical_agents_service.py:86`, `app/services/agentic_clinical_agents_service.py:87` | LLM failures are swallowed; no retry/backoff/timeout policy. |
| 7 | Context Window Management | ⚠️ Partial | `app/services/agentic_clinical_agents_service.py:80`, `app/services/agentic_clinical_agents_service.py:82`, `app/services/agentic_triage_service.py:167` | Fixed truncation/token caps exist, but no adaptive packing/budgeting. |
| 8 | Human-in-the-Loop (HITL) Checkpoints | ⚠️ Partial | `app/api/deps.py:49`, `app/api/deps.py:69`, `app/api/v1/routes/encounters.py:217` | Feature gating/RBAC exists, but no review/approve/reject flow for AI outputs. |
| 9 | Observability & Logging | ⚠️ Partial | `app/core/audit.py:15`, `app/core/audit.py:30`, `app/core/middleware.py:16` | General logging exists; AI-specific telemetry (latency/tokens/cost/run_id) is absent. |
| 10 | Security & Prompt Injection Defense | ⚠️ Partial | `app/core/middleware.py:96`, `app/services/agentic_clinical_agents_service.py:181`, `.env.example:37` | Auth and tenancy are solid, but injection defenses are minimal and secret handling is unsafe. |
| 11 | Multi-Agent Coordination | ⚠️ Partial | `app/services/agentic_clinical_agents_service.py:121`, `app/services/agentic_clinical_agents_service.py:199`, `app/services/agentic_clinical_agents_service.py:422` | Multiple specialist agents exist with no coordinator/conflict-resolution layer. |
| 12 | Termination Conditions | ⚠️ Partial | `app/services/agentic_clinical_agents_service.py:121`, `app/services/agentic_clinical_agents_service.py:193` | One-shot functions terminate by return; no explicit stop policy for iterative workflows. |
| 13 | Cost & Latency Budgets | ❌ Missing | `app/services/agentic_clinical_agents_service.py:82`, `app/core/config.py:20` | No configured/enforced cost, latency, or token budgets per request. |
| 14 | Evaluation & Testing Framework | ❌ Missing | `tests/test_encounter_api.py:30`, `tests/test_encounter_service.py:46`, `frontend/__tests__/queue-table.test.tsx:16` | Test coverage exists broadly, but no agent-specific behavioral/safety eval tests. |

---

## Step 2 - Detailed Findings

### 2) Structured System Prompt Maintenance
- Current State: Prompt content is embedded in service code.
- Risk: Prompt drift, hard reviews, no versioning/rollout controls.
- Affected Files: `app/services/agentic_clinical_agents_service.py`
- Code Smell Example:

```python
# app/services/agentic_clinical_agents_service.py:78
"content": "You are a clinical co-pilot. Provide concise, safety-first assistance.",
```

### 3) Memory Management (short/long-term)
- Current State: Context is loaded from encounter/background/prior records at invocation time.
- Risk: Limited continuity and no longitudinal AI memory.
- Affected Files: `app/services/agentic_clinical_agents_service.py`, `app/services/agentic_triage_service.py`
- Code Smell Example:

```python
# app/services/agentic_clinical_agents_service.py:114
.limit(5)
```

### 4) Tool/Function Registry
- Current State: Route handlers call concrete service functions directly.
- Risk: Harder scaling/governance and duplicated wiring.
- Affected Files: `app/api/v1/routes/encounters.py`, `app/services/agentic_clinical_agents_service.py`
- Code Smell Example:

```python
# app/api/v1/routes/encounters.py:264
result = await agentic_clinical_agents_service.run_differential_diagnosis_agent(...)
```

### 5) State Machine / Workflow Orchestration
- Current State: Encounter status updates are simple assignments.
- Risk: No formal state transitions for agent runs, retries, approvals, or resumability.
- Affected Files: `app/services/encounter_service.py`, `app/api/v1/routes/encounters.py`
- Code Smell Example:

```python
# app/services/encounter_service.py:505
encounter.status = payload.status
```

### 6) Error Handling & Retry Logic
- Current State: Catch-all exception handling returns `None`.
- Risk: Silent failures and undetected model degradation.
- Affected Files: `app/services/agentic_clinical_agents_service.py`
- Code Smell Example:

```python
# app/services/agentic_clinical_agents_service.py:86
except Exception:
    return None
```

### 7) Context Window Management
- Current State: Static truncation and max output token limits are used.
- Risk: Important context can be dropped unpredictably.
- Affected Files: `app/services/agentic_clinical_agents_service.py`, `app/services/agentic_triage_service.py`
- Code Smell Example:

```python
# app/services/agentic_clinical_agents_service.py:80
{"role": "user", "content": prompt[:5000]}
```

### 8) Human-in-the-Loop (HITL) Checkpoints
- Current State: AI is globally/clinic gated and RBAC protected.
- Risk: No explicit approve/reject/edit checkpoint for AI-generated recommendations.
- Affected Files: `app/api/deps.py`, `app/api/v1/routes/encounters.py`
- Code Smell Example:

```python
# app/api/v1/routes/encounters.py:227
_ = payload.regenerate
```

### 9) Observability & Logging
- Current State: Request audit and middleware logs exist.
- Risk: No AI run tracing for latency/cost/token/error outcomes.
- Affected Files: `app/core/audit.py`, `app/core/middleware.py`, `app/main.py`
- Code Smell Example:

```python
# app/core/audit.py:30
logger.info("AUDIT | user=%s action=%s %s | ts=%s | payload_hash=%s", ...)
```

### 10) Security & Prompt Injection Defense
- Current State: Good auth + tenant isolation; weak prompt hardening.
- Risk: Prompt injection and key leakage/compliance exposure.
- Affected Files: `.env.example`, `app/services/agentic_clinical_agents_service.py`, `app/core/middleware.py`
- Code Smell Example:

```env
# .env.example:37
OPENAI_API_KEY="sk-proj-..."
```

### 11) Multi-Agent Coordination
- Current State: Multiple specialized agents are implemented independently.
- Risk: Inconsistent outputs and no arbitration/provenance synthesis.
- Affected Files: `app/services/agentic_clinical_agents_service.py`, `app/api/v1/routes/encounters.py`
- Code Smell Example:

```python
# Independent agent functions, no coordinator layer
async def run_differential_diagnosis_agent(...):
async def run_order_recommendation_agent(...):
```

### 12) Termination Conditions
- Current State: Single-run function pattern exits on return.
- Risk: No explicit stop policy when iterative orchestration is introduced.
- Affected Files: `app/services/agentic_clinical_agents_service.py`
- Code Smell Example:

```python
# app/services/agentic_clinical_agents_service.py:193
"orchestration": "differential_diagnosis_v1"
```

### 13) Cost & Latency Budgets
- Current State: `max_output_tokens` is fixed; no budget enforcement.
- Risk: Uncontrolled cost and response-time variance.
- Affected Files: `app/services/agentic_clinical_agents_service.py`, `app/core/config.py`
- Code Smell Example:

```python
# app/services/agentic_clinical_agents_service.py:82
max_output_tokens=200
```

### 14) Evaluation & Testing Framework
- Current State: Existing tests focus on general API/service/UI behavior.
- Risk: Agent regressions and safety failures can pass CI unnoticed.
- Affected Files: `tests/test_encounter_api.py`, `tests/test_encounter_service.py`, `frontend/__tests__/`
- Code Smell Example:

```python
# tests/test_encounter_api.py:30
API = "/api/v1/encounters"
```

---

## Step 3 - Improvement Plan

### Priority: 🔴 Critical | 🟡 Important | 🟢 Nice-to-Have

#### Security & Prompt Injection Defense - 🔴 Critical
**What to build:** Secret hygiene and centralized prompt safety controls.

**Implementation steps:**
1. Replace leaked key in `.env.example` with a placeholder and rotate any exposed secret.
2. Add input sanitization + prompt policy utility for AI calls.
3. Add output validation and reject unsafe/invalid generations.

**Code scaffold to add:**
```python
# app/agentic/safety.py
def sanitize_user_text(text: str) -> str:
    risky = ["ignore previous instructions", "reveal system prompt"]
    lowered = text.lower()
    if any(token in lowered for token in risky):
        raise ValueError("Potential prompt injection pattern")
    return text
```

**Files to create/modify:**
- `.env.example` - remove real key and keep placeholder only
- `app/agentic/safety.py` - guardrail helpers
- `app/services/agentic_clinical_agents_service.py` - apply safety layer

**Estimated effort:** 1-2 days

#### Tool/Function Registry - 🔴 Critical
**What to build:** A centralized agent registry and dispatcher.

**Implementation steps:**
1. Define `AgentSpec` and registry map.
2. Register each agent in one location.
3. Route API calls through a generic invocation function.

**Code scaffold to add:**
```python
# app/agentic/registry.py
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

@dataclass(frozen=True)
class AgentSpec:
    name: str
    fn: Callable[..., Awaitable[dict[str, Any]]]

REGISTRY: dict[str, AgentSpec] = {}
```

**Files to create/modify:**
- `app/agentic/registry.py` - registry and metadata
- `app/api/v1/routes/encounters.py` - centralized dispatch
- `app/services/agentic_clinical_agents_service.py` - register handlers

**Estimated effort:** 1 day

#### Error Handling & Retry Logic - 🔴 Critical
**What to build:** Typed provider wrapper with retry/backoff and timeout.

**Implementation steps:**
1. Wrap provider calls with bounded retries.
2. Add timeout and explicit provider exception mapping.
3. Emit structured logs per attempt/failure.

**Code scaffold to add:**
```python
# app/agentic/provider.py
async def call_model(client, payload, retries: int = 3):
    for attempt in range(1, retries + 1):
        try:
            return await client.responses.create(**payload)
        except TimeoutError:
            if attempt == retries:
                raise
```

**Files to create/modify:**
- `app/agentic/provider.py` - provider wrapper
- `app/services/agentic_clinical_agents_service.py` - use wrapper
- `app/core/config.py` - retry/timeout settings

**Estimated effort:** 6-8 hours

#### Cost & Latency Budgets - 🔴 Critical
**What to build:** Configurable token/cost/latency budget enforcement.

**Implementation steps:**
1. Add budget settings in config.
2. Track usage per run and enforce hard limits.
3. Return budget-exceeded status and telemetry.

**Code scaffold to add:**
```python
class BudgetExceeded(Exception):
    pass

def enforce_latency_budget(latency_ms: int, max_latency_ms: int) -> None:
    if latency_ms > max_latency_ms:
        raise BudgetExceeded("latency budget exceeded")
```

**Files to create/modify:**
- `app/agentic/budget.py` - budget logic
- `app/core/config.py` - budget settings
- `app/services/agentic_clinical_agents_service.py` - runtime checks

**Estimated effort:** 1 day

#### Evaluation & Testing Framework - 🔴 Critical
**What to build:** Agent-specific backend and integration evaluation tests.

**Implementation steps:**
1. Add API tests for each `/ai/*` endpoint and gating behavior.
2. Add service-level tests for missing data, safety checks, and deterministic outputs.
3. Add CI stage for agent test suite.

**Code scaffold to add:**
```python
@pytest.mark.asyncio
async def test_triage_summary_returns_missing_information(client_provider, enc_id):
    resp = await client_provider.post(f"/api/v1/encounters/{enc_id}/ai/triage-summary", json={"regenerate": False})
    assert resp.status_code == 200
    assert "missing_information" in resp.json()
```

**Files to create/modify:**
- `tests/test_agentic_api.py` - endpoint tests
- `tests/test_agentic_services.py` - service tests
- `.github/workflows/ci.yml` - include agent tests

**Estimated effort:** 2-3 days

#### State Machine / Workflow Orchestration - 🟡 Important
**What to build:** Explicit run lifecycle state machine for agent invocations.

**Implementation steps:**
1. Define run states and transitions.
2. Persist run state and transition history.
3. Expose status polling endpoint for async workflows.

**Code scaffold to add:**
```python
from enum import Enum

class RunState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    NEEDS_REVIEW = "needs_review"
    COMPLETED = "completed"
    FAILED = "failed"
```

**Files to create/modify:**
- `app/agentic/workflow.py` - state transitions
- `app/schemas/encounter.py` - run status schemas
- `app/api/v1/routes/encounters.py` - workflow endpoints

**Estimated effort:** 2-3 days

#### Structured System Prompt Maintenance - 🟡 Important
**What to build:** Versioned prompt template registry.

**Implementation steps:**
1. Move prompt text to `app/agentic/prompts.py`.
2. Render prompts with strict variable inputs.
3. Add tests to prevent prompt variable drift.

**Code scaffold to add:**
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class PromptTemplate:
    name: str
    version: str
    system: str
    user: str
```

**Files to create/modify:**
- `app/agentic/prompts.py` - template source
- `app/services/agentic_clinical_agents_service.py` - prompt rendering
- `tests/test_agentic_prompts.py` - prompt contract tests

**Estimated effort:** 4-6 hours

#### Memory Management (short/long-term) - 🟡 Important
**What to build:** Persisted agent memory with retrieval policy.

**Implementation steps:**
1. Add model/migration to store AI runs and summarized outputs.
2. Retrieve prior relevant outputs for future runs.
3. Enforce retention and tenant isolation policies.

**Code scaffold to add:**
```python
class AgentMemory(BaseModel):
    __tablename__ = "agent_memory"
    agent_name: Mapped[str]
    encounter_id: Mapped[uuid.UUID]
    output_json: Mapped[dict]
```

**Files to create/modify:**
- `app/models/agent_memory.py` - memory entity
- `alembic/versions/*_add_agent_memory.py` - migration
- `app/services/agentic_clinical_agents_service.py` - memory read/write

**Estimated effort:** 1-2 days

#### Context Window Management - 🟡 Important
**What to build:** Context ranking and token-aware packing.

**Implementation steps:**
1. Rank context by clinical relevance/recency.
2. Pack within budget and record dropped segments.
3. Add tests for truncation edge cases.

**Code scaffold to add:**
```python
def pack_context(chunks: list[str], max_chars: int = 6000) -> str:
    out, used = [], 0
    for c in chunks:
        if used + len(c) > max_chars:
            break
        out.append(c)
        used += len(c)
    return "\n".join(out)
```

**Files to create/modify:**
- `app/agentic/context.py` - packing logic
- `app/services/agentic_clinical_agents_service.py` - usage
- `tests/test_agentic_context.py` - tests

**Estimated effort:** 4-6 hours

#### Human-in-the-Loop (HITL) Checkpoints - 🟡 Important
**What to build:** Clinician review/approval workflow for selected AI actions.

**Implementation steps:**
1. Introduce `needs_review` run state.
2. Add approve/reject endpoints with reviewer attribution.
3. Require approval before downstream actionable operations.

**Code scaffold to add:**
```python
class AgentReviewDecision(BaseModel):
    run_id: uuid.UUID
    approved: bool
    reviewer_id: uuid.UUID
    comment: str | None = None
```

**Files to create/modify:**
- `app/schemas/encounter.py` - review schemas
- `app/api/v1/routes/encounters.py` - review endpoints
- `frontend/components/encounters/detail/overview-tab.tsx` - review UI controls

**Estimated effort:** 2-3 days

#### Observability & Logging - 🟡 Important
**What to build:** AI run telemetry with correlation IDs and SLO metrics.

**Implementation steps:**
1. Add `run_id` for every AI call.
2. Log start/success/failure with model/latency/cost.
3. Add dashboards/alerts for error and latency thresholds.

**Code scaffold to add:**
```python
logger.info("agent_run", extra={
    "run_id": run_id,
    "agent": agent_name,
    "status": "success",
    "latency_ms": latency_ms,
})
```

**Files to create/modify:**
- `app/services/agentic_clinical_agents_service.py` - emit telemetry
- `app/core/audit.py` - include agent correlation metadata
- `README.md` - observability guidance

**Estimated effort:** 1 day

#### Multi-Agent Coordination - 🟢 Nice-to-Have
**What to build:** Coordinator that synthesizes outputs from specialist agents.

**Implementation steps:**
1. Add coordinator service.
2. Define conflict-resolution rules and confidence weighting.
3. Provide unified panel response with provenance.

**Code scaffold to add:**
```python
async def run_clinical_panel(ctx):
    results = {
        "differential": await run_differential(...),
        "orders": await run_orders(...),
        "med_safety": await run_med_safety(...),
    }
    return synthesize_panel(results)
```

**Files to create/modify:**
- `app/services/agentic_coordinator_service.py` - aggregator
- `app/api/v1/routes/encounters.py` - panel endpoint
- `app/schemas/encounter.py` - panel schema

**Estimated effort:** 2 days

#### Termination Conditions - 🟢 Nice-to-Have
**What to build:** Formal stop policy (steps/time/failure budget).

**Implementation steps:**
1. Define stop policy in config.
2. Enforce policy in workflow runner.
3. Return explicit termination reason metadata.

**Code scaffold to add:**
```python
from dataclasses import dataclass

@dataclass
class StopPolicy:
    max_steps: int = 6
    timeout_s: int = 12
    max_failures: int = 2
```

**Files to create/modify:**
- `app/agentic/workflow.py` - stop checks
- `app/core/config.py` - policy values
- `app/schemas/encounter.py` - termination metadata

**Estimated effort:** 4-6 hours

---

## Step 4 - Execution Roadmap

### Phase 1 - Foundation (Week 1)
- [ ] Fix #10: Secret hygiene + prompt safety baseline
- [ ] Fix #4: Agent registry/dispatcher
- [ ] Fix #6: Retry/timeout and typed error handling
- [ ] Fix #2: Prompt registry + versioning

### Phase 2 - Resilience (Week 2)
- [ ] Fix #5: Workflow state machine
- [ ] Fix #12: Explicit termination policies
- [ ] Fix #13: Cost/latency/token budgets
- [ ] Fix #7: Context packing and budgeted prompt assembly

### Phase 3 - Observability & Safety (Week 3)
- [ ] Fix #9: AI telemetry and tracing
- [ ] Fix #8: HITL checkpoints and approvals
- [ ] Fix #11: Multi-agent coordinator
- [ ] Fix #14: Agent-focused test/eval framework
- [ ] Fix #3: Longitudinal agent memory

---

## Immediate Actions (Critical)
1. Rotate the exposed OpenAI key and scrub it from `.env.example`.
2. Add resilient provider call wrapper with timeout/retry and structured error logging.
3. Add basic tests for `/api/v1/encounters/{id}/ai/*` endpoints.
