from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.dependencies import get_executor, get_registry, validate_agent_exists, validate_request_schema
from agents.registry.loader import AgentRegistry
from core.graph.executor import GraphExecutor
from core.schemas.base import AgentRequest, AgentResponse

router = APIRouter(prefix="/utility", tags=["utility"])


@router.post("/{agent_id}", response_model=AgentResponse)
async def invoke_utility_agent(
    agent_id: str,
    body: dict[str, Any],
    request: Request,
    registry: AgentRegistry = Depends(get_registry),
    executor: GraphExecutor = Depends(get_executor),
) -> AgentResponse:
    await validate_agent_exists(agent_id, registry)
    agent_config = registry.get(agent_id)
    if agent_config.category != "utility":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent is not in utility category")

    validated_body = await validate_request_schema(agent_id, body, registry)

    request_id = str(getattr(request.state, "request_id", validated_body.get("request_id", "")))
    session_id = str(validated_body.get("session_id", request_id or "utility-session"))

    agent_request = AgentRequest(
        request_id=request_id,
        agent_id=agent_id,
        session_id=session_id,
        payload=dict(validated_body.get("payload", {})),
        metadata=dict(validated_body.get("metadata", {})),
        created_at=validated_body.get("created_at", datetime.now(UTC)),
    )
    return await executor.execute(agent_request)


@router.get("/{agent_id}/health")
async def utility_agent_health(agent_id: str, registry: AgentRegistry = Depends(get_registry)) -> dict[str, str]:
    await validate_agent_exists(agent_id, registry)
    cfg = registry.get(agent_id)
    if cfg.category != "utility":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent is not in utility category")
    return {"status": "ok", "agent_id": agent_id}
