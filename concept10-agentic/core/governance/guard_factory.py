from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from agents.registry.loader import AgentConfig
from core.governance.validators import (
    OutputSchemaValidator,
    PIIRedactionValidator,
    PromptInjectionShield,
    ToxicityGuard,
)

if TYPE_CHECKING:
    import guardrails  # type: ignore


class GuardWrapper:
    """Lightweight guard wrapper used when guardrails runtime is unavailable."""

    def __init__(self, rail_spec: str, validators: dict[str, Any]):
        self.rail_spec = rail_spec
        self.validators = validators

    def parse(self, payload: dict[str, Any], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"validated_output": payload, "metadata": metadata or {}}


def _resolve_default_rail_spec(agent_config: AgentConfig) -> str:
    category_to_rail = {
        "orchestrator": "core/governance/rail_specs/orchestrator.rail",
        "utility": "core/governance/rail_specs/utility.rail",
        "specialist": "core/governance/rail_specs/specialist.rail",
        "human-in-loop": "core/governance/rail_specs/orchestrator.rail",
    }
    return category_to_rail.get(agent_config.category, "core/governance/rail_specs/orchestrator.rail")


def build_guard(agent_config: AgentConfig) -> "guardrails.Guard | GuardWrapper":
    rail_spec = agent_config.governance_profile or _resolve_default_rail_spec(agent_config)
    if not Path(rail_spec).exists():
        rail_spec = _resolve_default_rail_spec(agent_config)

    validators = {
        "PIIRedactionValidator": PIIRedactionValidator(),
        "PromptInjectionShield": PromptInjectionShield(),
        "OutputSchemaValidator": OutputSchemaValidator(),
        "ToxicityGuard": ToxicityGuard(),
    }

    try:
        import guardrails  # type: ignore

        guard = guardrails.Guard.from_rail(rail_spec)
        return guard
    except Exception:
        return GuardWrapper(rail_spec=rail_spec, validators=validators)
