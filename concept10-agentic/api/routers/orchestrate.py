from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from api.dependencies import (
    get_executor,
    get_registry,
    validate_agent_exists,
    validate_request_schema,
)
from agents.registry.loader import AgentRegistry
from core.graph.executor import GraphExecutor
from core.schemas.base import AgentRequest, AgentResponse, AgentStatus

router = APIRouter(prefix="/orchestrate", tags=["orchestrate"])

RUN_STATUS: dict[str, dict[str, Any]] = {}
RUN_DECISIONS: dict[str, str] = {}
RUN_LOCK = asyncio.Lock()


@router.post("/{agent_id}", response_model=AgentResponse)
async def orchestrate_agent(
    agent_id: str,
    body: dict[str, Any],
    request: Request,
    registry: AgentRegistry = Depends(get_registry),
    executor: GraphExecutor = Depends(get_executor),
) -> AgentResponse:
    await validate_agent_exists(agent_id, registry)
    validated_body = await validate_request_schema(agent_id, body, registry)

    request_id = str(getattr(request.state, "request_id", validated_body.get("request_id", "")))
    session_id = str(validated_body.get("session_id", request_id or "session-default"))

    payload = dict(validated_body.get("payload", {}))
    metadata = dict(validated_body.get("metadata", {}))

    agent_request = AgentRequest(
        request_id=request_id,
        agent_id=agent_id,
        session_id=session_id,
        payload=payload,
        metadata=metadata,
        created_at=validated_body.get("created_at", datetime.now(UTC)),
    )

    async with RUN_LOCK:
        RUN_STATUS[request_id] = {
            "status": "running",
            "agent_id": agent_id,
            "updated_at": datetime.now(UTC).isoformat(),
            "human_review_pending": False,
        }

    response = await executor.execute(agent_request)

    async with RUN_LOCK:
        RUN_STATUS[request_id] = {
            "status": response.status.value,
            "agent_id": agent_id,
            "updated_at": datetime.now(UTC).isoformat(),
            "human_review_pending": response.status == AgentStatus.pending,
            "error": getattr(response, "error_detail", None),
        }

    return response


@router.post("/{agent_id}/stream")
async def orchestrate_agent_stream(
    agent_id: str,
    body: dict[str, Any],
    request: Request,
    registry: AgentRegistry = Depends(get_registry),
    executor: GraphExecutor = Depends(get_executor),
) -> StreamingResponse:
    await validate_agent_exists(agent_id, registry)
    validated_body = await validate_request_schema(agent_id, body, registry)

    request_id = str(getattr(request.state, "request_id", validated_body.get("request_id", "")))
    session_id = str(validated_body.get("session_id", request_id or "session-default"))

    agent_request = AgentRequest(
        request_id=request_id,
        agent_id=agent_id,
        session_id=session_id,
        payload=dict(validated_body.get("payload", {})),
        metadata=dict(validated_body.get("metadata", {})),
        created_at=validated_body.get("created_at", datetime.now(UTC)),
    )

    async def event_stream():
        async with RUN_LOCK:
            RUN_STATUS[request_id] = {
                "status": "running",
                "agent_id": agent_id,
                "updated_at": datetime.now(UTC).isoformat(),
                "human_review_pending": False,
            }

        async for chunk in executor.stream_execute(agent_request):
            event = chunk.get("event", "chunk")
            data = chunk.get("data", {})
            if event == "error":
                async with RUN_LOCK:
                    RUN_STATUS[request_id] = {
                        "status": "error",
                        "agent_id": agent_id,
                        "updated_at": datetime.now(UTC).isoformat(),
                        "human_review_pending": False,
                        "error": data.get("error"),
                    }
            elif event == "state":
                state = data.get("state", {})
                async with RUN_LOCK:
                    RUN_STATUS[request_id] = {
                        "status": "pending" if state.get("human_review_pending") else "success",
                        "agent_id": agent_id,
                        "updated_at": datetime.now(UTC).isoformat(),
                        "human_review_pending": bool(state.get("human_review_pending")),
                        "error": state.get("error"),
                    }

            yield f"event: {event}\\n"
            yield f"data: {json.dumps(data, default=str)}\\n\\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{agent_id}/status/{request_id}")
async def orchestrate_status(agent_id: str, request_id: str) -> dict[str, Any]:
    async with RUN_LOCK:
        status_payload = RUN_STATUS.get(request_id)
    if status_payload is None or status_payload.get("agent_id") != agent_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run status not found")
    return {"request_id": request_id, **status_payload}


@router.post("/{agent_id}/approve/{request_id}")
async def orchestrate_approve(agent_id: str, request_id: str, body: dict[str, Any]) -> dict[str, Any]:
    decision = str(body.get("decision", "approved")).strip().lower()
    if decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="decision must be 'approved' or 'rejected'")

    async with RUN_LOCK:
        status_payload = RUN_STATUS.get(request_id)
        if status_payload is None or status_payload.get("agent_id") != agent_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run status not found")

        RUN_DECISIONS[request_id] = decision
        status_payload["status"] = "resumed"
        status_payload["human_review_pending"] = False
        status_payload["updated_at"] = datetime.now(UTC).isoformat()
        RUN_STATUS[request_id] = status_payload

    return {
        "request_id": request_id,
        "agent_id": agent_id,
        "decision": decision,
        "status": "resumed",
    }
