from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError

from api.dependencies import get_executor, get_registry
from agents.registry.loader import AgentRegistry
from core.graph.executor import GraphExecutor
from core.schemas.base import AgentError, AgentRequest, AgentResponse, AgentStatus
from core.schemas.domains.triage import TriageInput, TriageSummaryOutput
from observability.spans import get_trace_id
from observability.tracking import RequestTracker

router = APIRouter()

TRIAGE_AGENT_ID = "triage-summary-agent"
TRIAGE_RUN_STATUS: dict[str, dict[str, Any]] = {}
TRIAGE_REVIEW_DECISIONS: dict[str, dict[str, Any]] = {}
TRIAGE_REQUESTS: dict[str, AgentRequest] = {}
TRIAGE_LOCK = asyncio.Lock()


class ReviewDecisionPayload(BaseModel):
    approved: bool
    reviewed_by: str
    review_notes: str = ""


def _generate_spec_request_id() -> str:
    tracker = RequestTracker()
    try:
        return tracker.generate_request_id("spec")  # type: ignore[call-arg]
    except TypeError:
        tracker.set_agent_category("specialist")
        return tracker.generate_request_id()


def _extract_roles(request: Request) -> set[str]:
    state_roles: set[str] = set()
    for attr in ("role", "user_role"):
        value = getattr(request.state, attr, None)
        if isinstance(value, str) and value.strip():
            state_roles.add(value.strip().lower())

    for attr in ("roles", "user_roles"):
        value = getattr(request.state, attr, None)
        if isinstance(value, (list, tuple, set)):
            state_roles.update(str(item).strip().lower() for item in value if str(item).strip())

    header_role = request.headers.get("X-User-Role", "")
    if header_role.strip():
        state_roles.add(header_role.strip().lower())

    return state_roles


def _require_triage_access(request: Request) -> None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    roles = _extract_roles(request)
    if not roles.intersection({"nurse", "reception", "doctor", "admin"}):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role. Nurse or reception role minimum.",
        )


def _coerce_triage_output(response: AgentResponse) -> TriageSummaryOutput:
    payload = response.output
    if isinstance(payload, dict) and "agent_response" in payload and isinstance(payload["agent_response"], dict):
        agent_response_payload = payload["agent_response"]
        output_payload = agent_response_payload.get("output", {})
        return TriageSummaryOutput.model_validate(output_payload)

    if isinstance(payload, dict) and "output" in payload and isinstance(payload["output"], dict):
        return TriageSummaryOutput.model_validate(payload["output"])

    if isinstance(payload, dict):
        return TriageSummaryOutput.model_validate(payload)

    raise ValidationError.from_exception_data(
        "TriageSummaryOutput",
        [{"type": "model_type", "loc": ("output",), "msg": "Invalid triage output payload", "input": payload}],
    )


def _response_headers_dict(request_id: str, trace_id: str, langsmith_url: str | None) -> dict[str, str]:
    headers = {
        "X-Request-ID": request_id,
        "X-Trace-ID": trace_id,
    }
    if langsmith_url:
        headers["X-LangSmith-URL"] = langsmith_url
    return headers


def _map_agent_error_to_http(agent_error: AgentError, request_id: str) -> HTTPException:
    detail = {
        "message": agent_error.error_detail,
        "error_code": agent_error.error_code,
        "request_id": request_id,
    }
    lowered = f"{agent_error.error_code} {agent_error.error_detail}".lower()
    if "llm" in lowered or "anthropic" in lowered or "unavailable" in lowered:
        retry_after = str(int(agent_error.retry_after or 30))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            headers={"Retry-After": retry_after},
        )
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


@router.get("/ping")
async def ping_specialist() -> dict[str, str]:
    return {"status": "specialist_ok"}


@router.post(
    "/triage/summarise",
    response_model=TriageSummaryOutput,
    tags=["Triage"],
    summary="Generate outpatient triage summary",
    responses={
        200: {
            "description": "Triage summary generated",
            "content": {
                "application/json": {
                    "example": {
                        "visit_id": "VST-20260311-0009",
                        "request_id": "spec-1db56c8d-0e89-4f96-aef4-602d61ec4e91",
                        "acuity_level": "EMERGENT",
                        "acuity_rationale": "Chest pain with diaphoresis and tachycardia raises high-risk concern.",
                        "clinical_summary": {
                            "one_liner": "58M with acute chest pain, diaphoresis, tachycardia; needs urgent escalation.",
                            "presenting_problem": "High-risk chest pain presentation with associated autonomic symptoms.",
                            "vital_signs_interpretation": "HR elevated with borderline oxygenation; requires immediate physician review.",
                            "key_risk_factors": ["hypertension", "smoker", "family history CAD"],
                            "differential_considerations": ["acute coronary syndrome", "pulmonary embolism", "aortic syndrome"],
                            "recommended_workup": ["ECG", "serial troponin", "chest imaging", "urgent physician exam"]
                        },
                        "emergency_flags": [
                            {
                                "flag_code": "POSSIBLE_MI",
                                "description": "Chest pain with diaphoresis and radiation pattern.",
                                "confidence": 0.86,
                                "recommended_action": "Immediate physician evaluation and cardiac protocol.",
                                "escalation_sla_seconds": 60
                            }
                        ],
                        "special_handling_flags": [],
                        "immediate_action_required": True,
                        "alert_charge_nurse": True,
                        "alert_attending_physician": True,
                        "suggested_waiting_area": "acute",
                        "summary_generated_at": "2026-03-11T14:22:13.223801+00:00",
                        "model_confidence": 0.81,
                        "disclaimer": "AI-generated clinical aid. Must be reviewed by qualified clinician."
                    }
                }
            },
        }
    },
)
async def summarise_triage(
    body: TriageInput,
    request: Request,
    response: Response,
    registry: AgentRegistry = Depends(get_registry),
    executor: GraphExecutor = Depends(get_executor),
) -> TriageSummaryOutput:
    _require_triage_access(request)
    request_id = _generate_spec_request_id()

    triage_input = body.model_copy(update={"request_id": request_id})
    payload = triage_input.model_dump(mode="python")

    agent_request = AgentRequest(
        request_id=request_id,
        agent_id=TRIAGE_AGENT_ID,
        session_id=f"triage-{triage_input.visit_id}",
        payload={"triage_input": payload, **payload},
        metadata={"endpoint": "triage_summarise", "visit_id": triage_input.visit_id},
        created_at=datetime.now(UTC),
    )

    try:
        registry.get(TRIAGE_AGENT_ID)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Triage agent not registered") from exc

    async with TRIAGE_LOCK:
        TRIAGE_RUN_STATUS[request_id] = {
            "request_id": request_id,
            "visit_id": triage_input.visit_id,
            "status": "running",
            "updated_at": _now_iso(),
            "human_review_pending": False,
            "state": None,
        }
        TRIAGE_REQUESTS[request_id] = agent_request

    result = await executor.execute(agent_request)
    trace_id = get_trace_id()
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Trace-ID"] = trace_id
    if result.trace_url:
        response.headers["X-LangSmith-URL"] = result.trace_url

    if isinstance(result, AgentError) or result.status == AgentStatus.error:
        async with TRIAGE_LOCK:
            TRIAGE_RUN_STATUS[request_id].update(
                {
                    "status": "error",
                    "updated_at": _now_iso(),
                    "error": getattr(result, "error_detail", "triage execution failed"),
                }
            )
        _map_agent_error_to_http(result if isinstance(result, AgentError) else AgentError(
            request_id=result.request_id,
            agent_id=result.agent_id,
            output=result.output,
            trace_url=result.trace_url,
            duration_ms=result.duration_ms,
            created_at=result.created_at,
            error_code="INTERNAL_ERROR",
            error_detail="Triage execution failed",
            retry_after=None,
        ), request_id)

    try:
        triage_output = _coerce_triage_output(result)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Internal error while validating triage output",
                "request_id": request_id,
                "error": str(exc),
            },
        ) from exc

    async with TRIAGE_LOCK:
        TRIAGE_RUN_STATUS[request_id].update(
            {
                "status": "success",
                "updated_at": _now_iso(),
                "human_review_pending": False,
                "state": {"final_output": triage_output.model_dump(mode="json")},
            }
        )

    return triage_output


@router.post(
    "/triage/summarise/stream",
    tags=["Triage"],
    summary="Stream outpatient triage summary events",
)
async def summarise_triage_stream(
    body: TriageInput,
    request: Request,
    registry: AgentRegistry = Depends(get_registry),
    executor: GraphExecutor = Depends(get_executor),
) -> StreamingResponse:
    _require_triage_access(request)
    request_id = _generate_spec_request_id()
    triage_input = body.model_copy(update={"request_id": request_id})

    try:
        registry.get(TRIAGE_AGENT_ID)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Triage agent not registered") from exc

    agent_request = AgentRequest(
        request_id=request_id,
        agent_id=TRIAGE_AGENT_ID,
        session_id=f"triage-{triage_input.visit_id}",
        payload={"triage_input": triage_input.model_dump(mode="python")},
        metadata={"endpoint": "triage_summarise_stream", "visit_id": triage_input.visit_id},
        created_at=datetime.now(UTC),
    )

    async def event_stream():
        async with TRIAGE_LOCK:
            TRIAGE_RUN_STATUS[request_id] = {
                "request_id": request_id,
                "visit_id": triage_input.visit_id,
                "status": "running",
                "updated_at": _now_iso(),
                "human_review_pending": False,
                "state": None,
            }
            TRIAGE_REQUESTS[request_id] = agent_request

        yield "event: node_enter\n"
        yield f"data: {json.dumps({'node': 'validate_input', 'request_id': request_id, 'timestamp': _now_iso()})}\n\n"

        async for chunk in executor.stream_execute(agent_request):
            event = str(chunk.get("event", "chunk"))
            data = chunk.get("data", {})

            if event == "chunk":
                update = data.get("update", {})
                trace_steps = data.get("trace_steps", [])

                if isinstance(trace_steps, list) and trace_steps:
                    latest = trace_steps[-1]
                    if isinstance(latest, dict) and "node" in latest:
                        yield "event: node_enter\n"
                        yield f"data: {json.dumps({'node': latest.get('node'), 'request_id': request_id, 'timestamp': latest.get('timestamp_utc', _now_iso())}, default=str)}\n\n"

                governance_info = None
                if isinstance(update, dict):
                    for value in update.values():
                        if isinstance(value, dict) and ("governance_flags" in value or "redacted_fields" in value):
                            governance_info = {
                                "flags": value.get("governance_flags", []),
                                "redacted_fields": value.get("redacted_fields", []),
                            }
                            break
                if governance_info is not None:
                    yield "event: governance\n"
                    yield f"data: {json.dumps(governance_info, default=str)}\n\n"

                if isinstance(update, dict) and "llm_call" in update:
                    llm_payload = update.get("llm_call", {})
                    yield "event: llm_start\n"
                    yield f"data: {json.dumps({'request_id': request_id, 'model': 'claude-haiku-4-5'})}\n\n"
                    if isinstance(llm_payload, dict):
                        tool_results = llm_payload.get("tool_results", {})
                        llm_result = tool_results.get("llm_call", {}) if isinstance(tool_results, dict) else {}
                        if isinstance(llm_result, dict):
                            delta = llm_result.get("response")
                            if isinstance(delta, str) and delta:
                                yield "event: llm_chunk\n"
                                yield f"data: {json.dumps({'delta': delta})}\n\n"

            if event == "state":
                state_payload = data.get("state", {})
                async with TRIAGE_LOCK:
                    TRIAGE_RUN_STATUS[request_id] = {
                        "request_id": request_id,
                        "visit_id": triage_input.visit_id,
                        "status": "pending" if state_payload.get("human_review_pending") else "success",
                        "updated_at": _now_iso(),
                        "human_review_pending": bool(state_payload.get("human_review_pending")),
                        "state": state_payload,
                        "error": state_payload.get("error"),
                    }

                final_output = state_payload.get("final_output", {}) if isinstance(state_payload, dict) else {}
                if isinstance(final_output, dict):
                    triage_candidate = final_output.get("agent_response", {}).get("output", {})
                    if isinstance(triage_candidate, dict):
                        emergency_flags = triage_candidate.get("emergency_flags", [])
                        special_flags = triage_candidate.get("special_handling_flags", [])
                        yield "event: flags_raised\n"
                        yield f"data: {json.dumps({'emergency_flags': emergency_flags, 'special_handling_flags': special_flags}, default=str)}\n\n"

                        try:
                            triage_output = TriageSummaryOutput.model_validate(triage_candidate)
                            yield "event: complete\n"
                            yield f"data: {json.dumps(triage_output.model_dump(mode='json'), default=str)}\n\n"
                        except Exception:
                            pass

            if event == "error":
                async with TRIAGE_LOCK:
                    TRIAGE_RUN_STATUS[request_id].update(
                        {
                            "status": "error",
                            "updated_at": _now_iso(),
                            "error": data.get("error", "stream error"),
                        }
                    )
                error_payload = {
                    "request_id": request_id,
                    "agent_id": TRIAGE_AGENT_ID,
                    "status": "error",
                    "error_detail": str(data.get("error", "stream error")),
                }
                yield "event: error\n"
                yield f"data: {json.dumps(error_payload, default=str)}\n\n"

    headers = {
        "X-Request-ID": request_id,
        "X-Trace-ID": get_trace_id(),
    }
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)


@router.get(
    "/triage/status/{request_id}",
    tags=["Triage"],
    summary="Get triage graph execution status",
)
async def triage_status(request_id: str, request: Request) -> dict[str, Any]:
    _require_triage_access(request)
    async with TRIAGE_LOCK:
        status_payload = TRIAGE_RUN_STATUS.get(request_id)

    if status_payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run status not found")

    return status_payload


@router.post(
    "/triage/approve/{request_id}",
    tags=["Triage"],
    summary="Approve or reject triage human-review pause",
)
async def triage_approve(request_id: str, body: ReviewDecisionPayload, request: Request) -> dict[str, Any]:
    _require_triage_access(request)
    async with TRIAGE_LOCK:
        run_payload = TRIAGE_RUN_STATUS.get(request_id)
        if run_payload is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run status not found")
        original_request = TRIAGE_REQUESTS.get(request_id)

        state_payload = run_payload.get("state")
        if not isinstance(state_payload, dict):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No resumable state found for request")

        decision = "approved" if body.approved else "rejected"
        trace_steps = state_payload.get("trace_steps")
        if not isinstance(trace_steps, list):
            trace_steps = []
            state_payload["trace_steps"] = trace_steps

        trace_steps.append(
            {
                "timestamp_utc": _now_iso(),
                "node": "human_review_decision",
                "request_id": request_id,
                "reviewed_by": body.reviewed_by,
                "review_notes": body.review_notes,
                "decision": decision,
            }
        )

        context_payload = state_payload.get("context")
        if not isinstance(context_payload, dict):
            context_payload = {}
            state_payload["context"] = context_payload
        context_payload["human_decision"] = decision

        run_payload["human_review_pending"] = False
        run_payload["status"] = "resumed"
        run_payload["updated_at"] = _now_iso()
        run_payload["state"] = state_payload

        TRIAGE_REVIEW_DECISIONS[request_id] = {
            "approved": body.approved,
            "reviewed_by": body.reviewed_by,
            "review_notes": body.review_notes,
            "timestamp": _now_iso(),
        }
        TRIAGE_RUN_STATUS[request_id] = run_payload

    resumed_status = "resumed"
    if original_request is not None:
        resumed_request = original_request.model_copy(
            update={
                "payload": {
                    **original_request.payload,
                    "human_decision": "approved" if body.approved else "rejected",
                },
                "metadata": {
                    **original_request.metadata,
                    "reviewed_by": body.reviewed_by,
                    "review_notes": body.review_notes,
                    "review_decision": "approved" if body.approved else "rejected",
                },
            }
        )

        executor = get_executor(request)
        resumed_response = await executor.execute(resumed_request)
        async with TRIAGE_LOCK:
            TRIAGE_RUN_STATUS[request_id]["status"] = resumed_response.status.value
            TRIAGE_RUN_STATUS[request_id]["updated_at"] = _now_iso()
            TRIAGE_RUN_STATUS[request_id]["resume_result"] = resumed_response.model_dump(mode="json")
        resumed_status = resumed_response.status.value

    return {
        "request_id": request_id,
        "status": resumed_status,
        "decision": "approved" if body.approved else "rejected",
        "reviewed_by": body.reviewed_by,
    }


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
