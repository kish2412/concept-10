from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status

from agents.registry.loader import AgentRegistry
from core.context.manager import ContextManager
from core.graph.executor import GraphExecutor
from core.schemas.validators import SchemaValidator


def get_registry(request: Request) -> AgentRegistry:
    registry = getattr(request.app.state, "registry", None)
    if registry is None:
        raise HTTPException(status_code=500, detail="AgentRegistry not initialized")
    return registry


def get_context_manager(request: Request) -> ContextManager:
    context_manager = getattr(request.app.state, "context_manager", None)
    if context_manager is None:
        raise HTTPException(status_code=500, detail="ContextManager not initialized")
    return context_manager


def get_executor(request: Request) -> GraphExecutor:
    executor = getattr(request.app.state, "executor", None)
    if executor is None:
        raise HTTPException(status_code=500, detail="GraphExecutor not initialized")
    return executor


async def validate_agent_exists(agent_id: str, registry: AgentRegistry) -> None:
    try:
        registry.get(agent_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent not found: {agent_id}") from exc


async def validate_request_schema(agent_id: str, body: dict[str, Any], registry: AgentRegistry) -> dict[str, Any]:
    try:
        agent_config = registry.get(agent_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent not found: {agent_id}") from exc

    validator = SchemaValidator()
    try:
        model = validator.load_model(agent_config.input_schema)
        validated = model.model_validate(body)
        return validated.model_dump(mode="python")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Input schema validation failed", "error": str(exc)},
        ) from exc
