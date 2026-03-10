from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.schemas.validators import SchemaValidator

LOGGER = logging.getLogger(__name__)

Category = Literal["orchestrator", "utility", "specialist", "human-in-loop"]
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


class AgentConfig(BaseModel):
    """Single registry entry describing an agent contract and runtime controls."""

    model_config = ConfigDict(extra="forbid")

    id: str
    category: Category
    version: str
    description: str
    prompt_template: str
    input_schema: str
    output_schema: str
    tags: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    governance_profile: str
    langsmith_project: str
    otel_service_name: str
    human_review_required: bool
    max_context_tokens: int = Field(gt=0)

    @field_validator("version")
    @classmethod
    def validate_semver(cls, value: str) -> str:
        if not SEMVER_PATTERN.match(value):
            raise ValueError("version must be a semantic version string")
        return value


class AgentRegistry:
    """Loads and validates agent registry entries from YAML."""

    def __init__(self, registry_path: str = "agents/registry/agent_registry.yaml", project_root: str | None = None):
        self.registry_path = Path(registry_path)
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self._agents: dict[str, AgentConfig] = {}
        self.schema_validator = SchemaValidator()

    async def load(self) -> AgentRegistry:
        resolved_registry_path = self._resolve_path(str(self.registry_path))
        raw_text = await asyncio.to_thread(resolved_registry_path.read_text, encoding="utf-8")
        payload = yaml.safe_load(raw_text)

        if not isinstance(payload, dict) or not isinstance(payload.get("agents"), list):
            raise ValueError("Registry must contain an 'agents' list at the top level.")

        loaded_agents: dict[str, AgentConfig] = {}
        for entry in payload["agents"]:
            config = AgentConfig.model_validate(entry)
            if config.id in loaded_agents:
                raise ValueError(f"Duplicate agent id found: {config.id}")

            self._validate_file_path(config.prompt_template, config.id, "prompt_template")
            self._validate_file_path(config.governance_profile, config.id, "governance_profile")
            self._validate_schema_path(config.input_schema, config.id, "input_schema")
            self._validate_schema_path(config.output_schema, config.id, "output_schema")

            if self._is_deprecated_version(config.version):
                LOGGER.warning(
                    "Agent '%s' uses deprecated version '%s'. Consider migrating.",
                    config.id,
                    config.version,
                )

            loaded_agents[config.id] = config

        self._agents = loaded_agents
        return self

    def get(self, agent_id: str) -> AgentConfig:
        if agent_id not in self._agents:
            raise KeyError(f"Agent id not found: {agent_id}")
        return self._agents[agent_id]

    def list_by_category(self, category: Category) -> list[AgentConfig]:
        return [agent for agent in self._agents.values() if agent.category == category]

    def list_all(self) -> list[AgentConfig]:
        return list(self._agents.values())

    def _resolve_path(self, relative_or_absolute: str) -> Path:
        path = Path(relative_or_absolute)
        if path.is_absolute():
            return path
        return self.project_root / path

    def _validate_file_path(self, file_path: str, agent_id: str, field_name: str) -> None:
        resolved = self._resolve_path(file_path)
        if not resolved.exists() or not resolved.is_file():
            raise FileNotFoundError(
                f"Agent '{agent_id}' has invalid {field_name}: '{file_path}'"
            )

    def _validate_schema_path(self, dotted_path: str, agent_id: str, field_name: str) -> None:
        try:
            self.schema_validator.load_model(dotted_path)
        except (ValueError, TypeError) as exc:
            raise type(exc)(
                f"Agent '{agent_id}' has invalid {field_name}: '{dotted_path}'. {exc}"
            ) from exc

    @staticmethod
    def _is_deprecated_version(version: str) -> bool:
        prerelease = version.split("-", maxsplit=1)[1] if "-" in version else ""
        return any(token in prerelease.lower() for token in ("deprecated", "legacy", "eol"))


async def load_agent_registry(registry_path: str) -> dict[str, Any]:
    """Load agent registry YAML from disk for runtime orchestration."""
    path = Path(registry_path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Agent registry must be a mapping at the top level.")
    return data
