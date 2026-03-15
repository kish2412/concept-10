from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from agents.registry.loader import AgentConfig
from core.governance.audit_log import GovernanceAuditLog
from core.governance.guard_factory import build_guard
from core.governance.validators import (
    FailResult,
    OutputSchemaValidator,
    PIIRedactionValidator,
    PromptInjectionShield,
    ToxicityGuard,
)
if TYPE_CHECKING:
    from core.graph.state import OrchestrationState


def make_governance_node(agent_config: AgentConfig):
    guard = build_guard(agent_config)
    audit = GovernanceAuditLog()
    pii_validator = PIIRedactionValidator()
    injection_validator = PromptInjectionShield()
    schema_validator = OutputSchemaValidator()
    toxicity_validator = ToxicityGuard()
    
    # Hard flags that should block execution
    HARD_FAIL_FLAGS = {"prompt_injection_detected", "governance_guard_parse_failed", "toxicity_detected"}

    async def governance_node(state: "OrchestrationState") -> "OrchestrationState":
        request_id = state.get("request_id", "")
        task_text = str(state.get("context", {}).get("task", ""))
        output_payload = state.get("tool_results", {}).get("llm_call", {})

        flags: list[str] = []
        redacted_fields: list[str] = []

        try:
            injection_validator.validate(task_text)
        except FailResult as injection_result:
            flags.append("prompt_injection_detected")
            audit.append(
                request_id=request_id,
                validator_name="PromptInjectionShield",
                result="fail",
                details={"reason": injection_result.error_message},
            )

        redacted_input, input_redactions = pii_validator.validate(task_text)
        _, output_redactions = pii_validator.validate(output_payload)
        redacted_fields.extend(input_redactions)
        redacted_fields.extend(output_redactions)

        if redacted_fields:
            state.setdefault("context", {})["task"] = redacted_input
            flags.append("pii_redacted")
            audit.append(
                request_id=request_id,
                validator_name="PIIRedactionValidator",
                result="redacted",
                redacted_fields=sorted(set(redacted_fields)),
            )

        schema_result = schema_validator.validate(agent_config, output_payload if isinstance(output_payload, dict) else {})
        if isinstance(schema_result, FailResult):
            flags.append("schema_validation_failed")
            audit.append(
                request_id=request_id,
                validator_name="OutputSchemaValidator",
                result="fail",
                details={"reason": schema_result.error_message},
            )

        toxicity_result = toxicity_validator.validate(str(output_payload))
        if isinstance(toxicity_result, FailResult):
            flags.append("toxicity_detected")
            audit.append(
                request_id=request_id,
                validator_name="ToxicityGuard",
                result="fail",
                details={"reason": toxicity_result.error_message},
            )

        parsed_payload = None
        try:
            parse_result = guard.parse(output_payload if isinstance(output_payload, dict) else {"output": output_payload}, metadata={"request_id": request_id})
            if isinstance(parse_result, tuple) and len(parse_result) > 0:
                parsed_payload = parse_result[0]
            else:
                parsed_payload = parse_result
        except Exception as exc:
            flags.append("guard_parse_failed")
            audit.append(
                request_id=request_id,
                validator_name="Guard.parse",
                result="fail",
                details={"reason": str(exc)},
            )

        if parsed_payload is not None:
            state.setdefault("context", {})["validated_payload"] = parsed_payload

        state["governance_flags"] = sorted(set(state.get("governance_flags", []) + flags))
        state.setdefault("trace_steps", []).append(
            {
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "node": "governance",
                "request_id": request_id,
                "flags": list(state["governance_flags"]),
                "redacted_fields": sorted(set(redacted_fields)),
            }
        )
        state["current_node"] = "governance"

        # Only set error for hard-fail flags
        if any(flag in HARD_FAIL_FLAGS for flag in state["governance_flags"]):
            state["error"] = "governance_validation_failed"

        return state

    return governance_node
