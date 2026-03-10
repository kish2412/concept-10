from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from agents.registry.categorizer import AgentCategorizer
from agents.registry.loader import AgentConfig, AgentRegistry, Category

router = APIRouter(prefix="/agents", tags=["agents"])

_registry_lock = asyncio.Lock()
_registry: AgentRegistry | None = None


class AgentConfigPublic(BaseModel):
    id: str
    category: Category
    version: str
    description: str
    prompt_template: str
    input_schema: str
    output_schema: str
    tags: list[str]
    tools: list[str]
    governance_profile: str
    langsmith_project: str
    otel_service_name: str
    human_review_required: bool
    max_context_tokens: int


class AgentListResponse(BaseModel):
    items: list[AgentConfigPublic]
    page: int
    size: int
    total: int


async def _get_registry() -> AgentRegistry:
    global _registry
    if _registry is not None:
        return _registry

    async with _registry_lock:
        if _registry is None:
            _registry = await AgentRegistry().load()

    return _registry


def _to_public(agent: AgentConfig) -> AgentConfigPublic:
    return AgentConfigPublic.model_validate(agent.model_dump())


@router.get("", response_model=AgentListResponse)
async def list_agents(
    category: Category | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> AgentListResponse:
    registry = await _get_registry()
    agents = registry.list_by_category(category) if category else registry.list_all()

    start = (page - 1) * size
    end = start + size
    paginated = agents[start:end]

    return AgentListResponse(
        items=[_to_public(agent) for agent in paginated],
        page=page,
        size=size,
        total=len(agents),
    )


@router.get("/graph")
async def get_agents_graph(
    orchestrator_id: str | None = Query(default=None, description="Orchestrator agent id"),
) -> dict[str, list[str]]:
    registry = await _get_registry()
    categorizer = AgentCategorizer(registry)

    if orchestrator_id:
        try:
            return categorizer.build_execution_graph(orchestrator_id)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    orchestrators = categorizer.get_orchestrators()
    full_graph: dict[str, list[str]] = {}
    for orchestrator in orchestrators:
        full_graph.update(categorizer.build_execution_graph(orchestrator.id))
    return full_graph


@router.get("/{agent_id}", response_model=AgentConfigPublic)
async def get_agent(agent_id: str) -> AgentConfigPublic:
    registry = await _get_registry()
    try:
        return _to_public(registry.get(agent_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
