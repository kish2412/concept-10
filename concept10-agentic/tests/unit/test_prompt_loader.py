from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from agents.registry.loader import AgentConfig
from core.prompts.template_loader import PromptLoader, PromptRenderError


def test_prompt_loader_renders_jinja_template(tmp_path: Path):
    template_path = tmp_path / "template.j2"
    template_path.write_text("Hello {{ name }}", encoding="utf-8")

    loader = PromptLoader(project_root=tmp_path)
    rendered = loader.render("template.j2", {"name": "Concept10"})

    assert rendered == "Hello Concept10"


def test_prompt_loader_enforces_token_limit(tmp_path: Path):
    templates_dir = tmp_path / "core" / "prompts" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "small_limit.j2").write_text("{{ task }}", encoding="utf-8")

    loader = PromptLoader(project_root=tmp_path)
    cfg = AgentConfig(
        id="tiny-agent",
        category="utility",
        version="1.0.0",
        description="tiny",
        prompt_template="core/prompts/templates/small_limit.j2",
        input_schema="core.schemas.base.AgentRequest",
        output_schema="core.schemas.base.AgentResponse",
        tags=[],
        tools=[],
        governance_profile="core/governance/rail_specs/utility.rail",
        langsmith_project="tiny",
        otel_service_name="tiny",
        human_review_required=False,
        max_context_tokens=5,
    )

    with pytest.raises(PromptRenderError) as exc_info:
        loader.render_system(
            cfg,
            {
                "request_id": "req-1",
                "task": "x" * 200,
                "timestamp_utc": datetime.now(UTC),
            },
        )

    assert "exceeds" in str(exc_info.value)
    assert exc_info.value.context["agent_id"] == "tiny-agent"
