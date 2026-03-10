# Creating New Agent

## Goal

Add a new agent that is discoverable via registry APIs and executable through orchestration routes.

## Step 1: Choose Agent Category

Allowed categories (validated by `AgentConfig`):

- `orchestrator`
- `utility`
- `specialist`
- `human-in-loop`

## Step 2: Prepare Dependencies

Before adding registry entry, ensure these exist:

- Prompt template file (example: `core/prompts/templates/specialist.j2`)
- Governance rail/profile file (example: `core/governance/rail_specs/specialist.rail`)
- Input schema class path (must resolve to a Pydantic model)
- Output schema class path (must resolve to a Pydantic model)

## Step 3: Add Registry Entry

Edit `agents/registry/agent_registry.yaml` and add a new item under `agents`.

Required fields:

- `id`
- `category`
- `version` (semantic version)
- `description`
- `prompt_template`
- `input_schema`
- `output_schema`
- `tools`
- `governance_profile`
- `langsmith_project`
- `otel_service_name`
- `human_review_required`
- `max_context_tokens`

Example:

```yaml
- id: claims-audit-specialist
  category: specialist
  version: 1.0.0
  description: Reviews claim anomalies and generates audit summary.
  prompt_template: core/prompts/templates/specialist.j2
  input_schema: core.schemas.base.AgentRequest
  output_schema: core.schemas.base.AgentResponse
  tags: [claims, audit]
  tools:
    - policy-retrieval-utility
  governance_profile: core/governance/rail_specs/specialist.rail
  langsmith_project: concept10-claims-audit
  otel_service_name: agent.claims.audit.specialist
  human_review_required: false
  max_context_tokens: 8000
```

## Step 4: Validate Registry Load

Run:

```bash
pytest tests/integration/test_registry_loader.py
```

Or start app and verify:

- `GET /agents` includes your new `id`.
- `GET /agents/{id}` resolves successfully.

## Step 5: Execute a Smoke Request

Call:

```http
POST /orchestrate/{agent_id}
```

Minimal body shape:

```json
{
  "request_id": "local-test-1",
  "agent_id": "claims-audit-specialist",
  "session_id": "session-1",
  "payload": {},
  "metadata": {}
}
```

## Step 6: Add Tests

At minimum:

- Integration test verifying agent appears in registry/API list.
- Execution-path test for success and failure behavior.

## Common Failure Modes

- Invalid semver in `version`.
- Missing prompt/governance file path.
- Invalid dotted path for schema class.
- Category not in allowed literal values.
- Schema does not inherit expected request/response base model.

## Definition of Done

- Registry entry loads without error.
- Agent visible via `/agents` APIs.
- Smoke orchestration call returns valid response.
- Tests updated and passing.
