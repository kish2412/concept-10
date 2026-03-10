from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError

from agents.registry.loader import AgentConfig
from core.prompts.variables import SystemPromptVariables


class PromptRenderError(RuntimeError):
    """Raised when prompt rendering or validation fails."""

    def __init__(self, message: str, *, context: dict[str, Any]):
        super().__init__(message)
        self.context = context


class PromptLoader:
    """Jinja2-backed prompt loader with rendering guardrails."""

    def __init__(self, project_root: str | Path | None = None):
        root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self.project_root = root
        self.environment = Environment(
            loader=FileSystemLoader(
                [
                    str(self.project_root),
                    str(self.project_root / "core" / "prompts" / "templates"),
                    str(self.project_root / "core" / "prompts"),
                ]
            ),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
        )

    def render(self, template_path: str, context: dict[str, Any]) -> str:
        normalized_template = self._normalize_template_path(template_path)
        try:
            template = self.environment.get_template(normalized_template)
            return template.render(**context)
        except TemplateError as exc:
            raise PromptRenderError(
                f"Failed to render template '{template_path}'",
                context={
                    "template_path": template_path,
                    "normalized_template": normalized_template,
                    "context_keys": sorted(context.keys()),
                    "error": str(exc),
                },
            ) from exc

    def render_system(self, agent_config: AgentConfig, runtime_ctx: dict[str, Any]) -> str:
        request_id = str(runtime_ctx.get("request_id", ""))
        if not request_id:
            raise PromptRenderError(
                "request_id is required for traceability",
                context={"agent_id": agent_config.id, "runtime_ctx_keys": sorted(runtime_ctx.keys())},
            )

        common_variables = SystemPromptVariables(
            agent_id=agent_config.id,
            request_id=request_id,
            timestamp_utc=runtime_ctx.get("timestamp_utc", datetime.now(UTC)),
            compliance_mode=str(runtime_ctx.get("compliance_mode", "standard")),
            user_tier=str(runtime_ctx.get("user_tier", "standard")),
        )

        merged_context = {**runtime_ctx, **common_variables.model_dump(mode="json")}
        rendered = self.render(agent_config.prompt_template, merged_context)

        token_count = self._estimate_tokens(rendered)
        if token_count > agent_config.max_context_tokens:
            raise PromptRenderError(
                "Rendered prompt exceeds agent max_context_tokens",
                context={
                    "agent_id": agent_config.id,
                    "template_path": agent_config.prompt_template,
                    "token_count": token_count,
                    "max_context_tokens": agent_config.max_context_tokens,
                    "request_id": request_id,
                },
            )

        return rendered

    def _normalize_template_path(self, template_path: str) -> str:
        raw_path = Path(template_path)
        if raw_path.is_absolute():
            try:
                return raw_path.relative_to(self.project_root).as_posix()
            except ValueError:
                return raw_path.as_posix()
        return raw_path.as_posix()

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        # Simple approximation to avoid hard-coupling loader to a specific tokenizer.
        return max(1, (len(text) + 3) // 4)
