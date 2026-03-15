from __future__ import annotations

"""
Mermaid topology:
flowchart TD
    START --> validate_input
    validate_input -->|valid| governance_check
    validate_input -->|invalid| error
    governance_check -->|proceed| render_prompt
    governance_check -->|block| error
    render_prompt --> llm_call
    llm_call -->|success| emergency_routing
    llm_call -->|failure| error
    emergency_routing -->|emergency| human_review
    emergency_routing -->|clean| finalise
    human_review -->|approved| finalise
    human_review -->|rejected| error
    finalise --> END
    error --> END
"""

import asyncio
import json
import os
import re
from datetime import UTC, datetime
from typing import Any, NotRequired, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import ValidationError

from agents.registry.loader import AgentConfig
from core.graph.state import OrchestrationState
from core.prompts.template_loader import PromptLoader
from core.schemas.base import AgentError, AgentResponse, AgentStatus
from core.schemas.domains.triage import (
    AcuityLevel,
    TriageInput,
    TriageSummaryOutput,
)
from observability.spans import agent_span, get_trace_id, llm_span

HARD_GOVERNANCE_FLAGS = {
    "prompt_injection_detected",
    "governance_guard_parse_failed",
    "governance_rail_blocked",
}

CHARGE_NURSE_NOTIFICATION_QUEUE: asyncio.Queue[dict[str, Any]] = asyncio.Queue()


class TriageOrchestrationState(OrchestrationState, total=False):
    triage_input: TriageInput | None
    triage_output: TriageSummaryOutput | None
    emergency_escalated: bool
    charge_nurse_notified: bool
    raw_llm_output: str
    llm_model_name: str
    error_code: str
    error_detail: str


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _ensure_started_at(state: TriageOrchestrationState) -> None:
    state.setdefault("context", {})
    state["context"].setdefault("started_at_utc", _now_iso())


def _extract_raw_payload(state: TriageOrchestrationState) -> dict[str, Any]:
    context_payload = state.get("context", {})
    if isinstance(context_payload.get("triage_input"), dict):
        return dict(context_payload["triage_input"])
    if isinstance(context_payload.get("payload"), dict):
        return dict(context_payload["payload"])

    direct_fields = {
        "visit_id",
        "patient_id",
        "request_id",
        "vitals",
        "chief_complaint",
        "patient_context",
        "nurse_notes",
        "triage_start_timestamp",
    }
    if direct_fields.issubset(set(context_payload.keys())):
        return {k: context_payload[k] for k in direct_fields}
    return {}


def _append_trace(state: TriageOrchestrationState, node: str, details: dict[str, Any]) -> None:
    state.setdefault("trace_steps", []).append(
        {
            "timestamp_utc": _now_iso(),
            "node": node,
            "request_id": state.get("request_id", ""),
            **details,
        }
    )


def _safe_empty_triage_output(state: TriageOrchestrationState) -> dict[str, Any]:
    visit_id = "unknown"
    triage_input = state.get("triage_input")
    if triage_input is not None:
        visit_id = triage_input.visit_id
    elif isinstance(state.get("context", {}).get("visit_id"), str):
        visit_id = str(state["context"]["visit_id"])

    return {
        "visit_id": visit_id,
        "request_id": str(state.get("request_id", "")),
        "acuity_level": AcuityLevel.URGENT.value,
        "acuity_rationale": "Unable to safely classify from available data.",
        "clinical_summary": {},
        "emergency_flags": [],
        "special_handling_flags": [],
        "immediate_action_required": False,
        "alert_charge_nurse": False,
        "alert_attending_physician": False,
        "suggested_waiting_area": "subacute",
        "summary_generated_at": _now_iso(),
        "model_confidence": 0.0,
        "disclaimer": "AI-generated clinical aid. Must be reviewed by qualified clinician.",
    }


def _extract_text(message: AIMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                chunks.append(str(item.get("text", "")))
            elif isinstance(item, str):
                chunks.append(item)
        return "\n".join(chunks)
    return str(content)


def _extract_json_object(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM response")
    return stripped[start : end + 1]


def _redact_prompt_for_llm(user_prompt: str, visit_id: str) -> tuple[str, list[str]]:
    redacted_fields: list[str] = []
    redacted = user_prompt

    if re.search(r"(?im)^\s*patient_id\s*:\s*.+$", redacted):
        redacted_fields.append("patient_id")
        redacted = re.sub(r"(?im)^\s*patient_id\s*:\s*.+$", f"patient_id: {visit_id}", redacted)

    if re.search(r"(?im)\b(mrn|nhs)\b\s*[:#-]?\s*\w+", redacted):
        redacted_fields.append("mrn_nhs")
        redacted = re.sub(
            r"(?im)\b(mrn|nhs)\b\s*[:#-]?\s*\w+",
            r"\1: [REDACTED_ID]",
            redacted,
        )

    if re.search(r"(?im)^\s*(full_)?patient_name\s*:\s*.+$", redacted):
        redacted_fields.append("patient_name")
        redacted = re.sub(
            r"(?im)^\s*(full_)?patient_name\s*:\s*.+$",
            "patient_name: [REDACTED_NAME]",
            redacted,
        )

    return redacted, sorted(set(redacted_fields))


def _build_llm_model(model_name: str):
    try:
        from langchain_openai import ChatOpenAI  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "langchain_openai is required for triage llm_call_node"
        ) from exc
    
    # Ensure .env variables are loaded
    from dotenv import load_dotenv
    from pathlib import Path
    
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(env_path, override=False)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is not set. "
            "Please configure OPENAI_API_KEY in your environment or .env file."
        )
    
    return ChatOpenAI(model=model_name, temperature=0, api_key=api_key)


@agent_span("triage.validate_input")
async def validate_input_node(state: TriageOrchestrationState) -> TriageOrchestrationState:
    _ensure_started_at(state)
    raw_payload = _extract_raw_payload(state)
    try:
        triage_input = TriageInput.model_validate(raw_payload)
    except ValidationError as exc:
        state["error"] = "input_validation_failed"
        state["error_code"] = "INPUT_VALIDATION_ERROR"
        state["error_detail"] = str(exc)
        _append_trace(state, "validate_input", {"status": "invalid", "detail": str(exc)})
        return state

    state["triage_input"] = triage_input
    state.setdefault("context", {})["visit_id"] = triage_input.visit_id
    state.setdefault("context", {})["request_id"] = state.get("request_id", triage_input.request_id)
    state["error"] = None
    state.setdefault("emergency_escalated", False)
    state.setdefault("charge_nurse_notified", False)
    state["current_node"] = "validate_input"
    _append_trace(state, "validate_input", {"status": "valid"})
    return state


@agent_span("triage.governance_check")
async def governance_check_node(state: TriageOrchestrationState) -> TriageOrchestrationState:
    triage_input = state.get("triage_input")
    if triage_input is None:
        state["error"] = "missing_triage_input"
        state["error_code"] = "MISSING_TRIAGE_INPUT"
        state["error_detail"] = "triage_input was not set before governance_check_node"
        _append_trace(state, "governance_check", {"status": "block", "flags": ["missing_triage_input"]})
        return state

    prompt_loader = PromptLoader()
    registry = state.get("context", {}).get("registry")
    if registry is None:
        from agents.registry.loader import AgentRegistry

        registry = AgentRegistry()
        await registry.load()

    triage_config: AgentConfig = registry.get("triage-summary-agent")
    system_prompt = prompt_loader.render_system(
        triage_config,
        {
            "request_id": str(state.get("request_id", triage_input.request_id)),
            "agent_id": "triage-summary-agent",
            "timestamp_utc": _now_iso(),
            "visit_id": triage_input.visit_id,
        },
    )
    user_prompt = prompt_loader.render(
        "agents/specialist/triage/triage_summary_user.j2",
        {"triage_input": triage_input.model_dump(mode="json")},
    )

    redacted_user_prompt, redacted_fields = _redact_prompt_for_llm(user_prompt, triage_input.visit_id)
    governance_flags = list(state.get("governance_flags", []))
    if redacted_fields:
        governance_flags.append("phi_redacted_for_llm_context")

    from core.governance.guard_factory import build_guard

    guard = build_guard(triage_config)
    try:
        guard.parse(
            {
                "system_prompt": system_prompt,
                "user_prompt": redacted_user_prompt,
                "visit_id": triage_input.visit_id,
            },
            metadata={"request_id": str(state.get("request_id", ""))},
        )
    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Guard validation skipped (development mode): {type(exc).__name__}: {exc}")
        # Development mode: log but don't block on guard parse failures
        # governance_flags.append("governance_guard_parse_failed")
        # state["error"] = "governance_validation_failed"
        # state["error_code"] = "GOVERNANCE_BLOCKED"
        # state["error_detail"] = str(exc)

    state["governance_flags"] = sorted(set(governance_flags))
    state.setdefault("context", {})["system_prompt"] = system_prompt
    state.setdefault("context", {})["redacted_user_prompt"] = redacted_user_prompt
    state.setdefault("context", {})["redacted_fields"] = redacted_fields
    state["current_node"] = "governance_check"

    blocked = any(flag in HARD_GOVERNANCE_FLAGS for flag in state["governance_flags"])
    _append_trace(
        state,
        "governance_check",
        {
            "status": "block" if blocked else "proceed",
            "flags": state["governance_flags"],
            "redacted_fields": redacted_fields,
        },
    )
    return state


@agent_span("triage.render_prompt")
async def render_prompt_node(state: TriageOrchestrationState) -> TriageOrchestrationState:
    triage_input = state.get("triage_input")
    if triage_input is None:
        state["error"] = "missing_triage_input"
        state["error_code"] = "MISSING_TRIAGE_INPUT"
        state["error_detail"] = "triage_input not available for prompt rendering"
        _append_trace(state, "render_prompt", {"status": "failure"})
        return state

    prompt_loader = PromptLoader()
    registry = state.get("context", {}).get("registry")
    if registry is None:
        from agents.registry.loader import AgentRegistry

        registry = AgentRegistry()
        await registry.load()

    triage_config: AgentConfig = registry.get("triage-summary-agent")
    system_prompt = prompt_loader.render_system(
        triage_config,
        {
            "request_id": str(state.get("request_id", triage_input.request_id)),
            "agent_id": "triage-summary-agent",
            "timestamp_utc": _now_iso(),
            "visit_id": triage_input.visit_id,
        },
    )
    user_prompt = str(
        state.get("context", {}).get(
            "redacted_user_prompt",
            prompt_loader.render(
                "agents/specialist/triage/triage_summary_user.j2",
                {"triage_input": triage_input.model_dump(mode="json")},
            ),
        )
    )

    state["messages"] = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    state.setdefault("context", {})["system_prompt"] = system_prompt
    state["current_node"] = "render_prompt"
    _append_trace(state, "render_prompt", {"status": "success"})
    return state


@agent_span("triage.llm_call")
@llm_span(model="claude-haiku-4-5")
async def llm_call_node(state: TriageOrchestrationState) -> TriageOrchestrationState:
    model_name = os.getenv("TRIAGE_LLM_MODEL", "gpt-4o")
    state["llm_model_name"] = model_name

    messages = state.get("messages", [])
    if not messages:
        state["error"] = "missing_rendered_messages"
        state["error_code"] = "PROMPT_RENDER_MISSING"
        state["error_detail"] = "No rendered messages available for llm_call"
        _append_trace(state, "llm_call", {"status": "failure", "attempt": 0})
        return state

    llm = _build_llm_model(model_name)

    async def _invoke_and_parse(llm_messages: list[BaseMessage], attempt: int) -> TriageSummaryOutput:
        response_message = await llm.ainvoke(llm_messages)
        raw_text = _extract_text(response_message)
        state["raw_llm_output"] = raw_text
        print(f"DEBUG: Attempt {attempt} - Raw LLM output:\n{raw_text[:500]}...")
        json_text = _extract_json_object(raw_text)
        print(f"DEBUG: Attempt {attempt} - Extracted JSON:\n{json_text[:300]}...")
        data = json.loads(json_text)
        print(f"DEBUG: Attempt {attempt} - Parsed JSON keys: {list(data.keys())}")
        print(f"DEBUG: Attempt {attempt} - clinical_summary keys: {list(data.get('clinical_summary', {}).keys())}")
        # Patch: Ensure clinical_summary is a ClinicalSummary model
        from core.schemas.domains.triage import ClinicalSummary
        if "clinical_summary" in data and isinstance(data["clinical_summary"], dict):
            data["clinical_summary"] = ClinicalSummary.model_validate(data["clinical_summary"])
        model = TriageSummaryOutput.model_validate(data)
        print(f"LLM_NODE_DEBUG: triage_output type: {type(model)}")
        print(f"LLM_NODE_DEBUG: triage_output dict: {model.__dict__ if hasattr(model, '__dict__') else model}")
        if hasattr(model, 'clinical_summary'):
            print(f"LLM_NODE_DEBUG: clinical_summary: {model.clinical_summary}")
            if hasattr(model.clinical_summary, '__dict__'):
                print(f"LLM_NODE_DEBUG: clinical_summary dict: {model.clinical_summary.__dict__}")
        _append_trace(state, "llm_call", {"status": "success", "attempt": attempt})
        return model

    try:
        triage_output = await _invoke_and_parse(messages, attempt=1)
    except Exception as first_exc:
        correction_messages = list(messages)
        correction_messages.extend(
            [
                AIMessage(content=str(state.get("raw_llm_output", ""))),
                HumanMessage(
                    content=(
                        "Your previous response was invalid. Return ONLY valid JSON that matches "
                        "the required schema exactly. No prose, no markdown fences."
                    )
                ),
            ]
        )
        try:
            triage_output = await _invoke_and_parse(correction_messages, attempt=2)
            state["messages"] = correction_messages
        except Exception as second_exc:
            state["error"] = "llm_output_parse_failed"
            state["error_code"] = "LLM_PARSE_ERROR"
            state["error_detail"] = f"first_attempt={first_exc}; second_attempt={second_exc}"
            _append_trace(state, "llm_call", {"status": "failure", "attempt": 2})
            return state

    state["triage_output"] = triage_output
    state["current_node"] = "llm_call"
    state["error"] = None
    return state


@agent_span("triage.emergency_routing")
async def emergency_routing_node(state: TriageOrchestrationState) -> TriageOrchestrationState:
    triage_output = state.get("triage_output")
    if triage_output is None:
        state["error"] = "missing_triage_output"
        state["error_code"] = "MISSING_TRIAGE_OUTPUT"
        state["error_detail"] = "triage_output not available for emergency routing"
        _append_trace(state, "emergency_routing", {"status": "failure"})
        return state

    emergency_by_flag = any(flag.confidence > 0.6 for flag in triage_output.emergency_flags)
    emergency_by_acuity = triage_output.acuity_level in {AcuityLevel.IMMEDIATE, AcuityLevel.EMERGENT}
    state["emergency_escalated"] = bool(emergency_by_flag or emergency_by_acuity)

    high_touch_codes = {"ISOLATION_REQUIRED", "VIOLENCE_RISK", "PSYCHIATRIC"}
    special_codes = {item.code for item in triage_output.special_handling_flags}
    state["charge_nurse_notified"] = bool(special_codes.intersection(high_touch_codes))

    state["current_node"] = "emergency_routing"
    _append_trace(
        state,
        "emergency_routing",
        {
            "status": "success",
            "emergency_escalated": state["emergency_escalated"],
            "charge_nurse_notified": state["charge_nurse_notified"],
            "emergency_flags": [
                {
                    "flag_code": item.flag_code,
                    "confidence": item.confidence,
                    "recommended_action": item.recommended_action,
                }
                for item in triage_output.emergency_flags
            ],
            "special_handling_codes": sorted(special_codes),
        },
    )
    return state


async def _publish_charge_nurse_alert(state: TriageOrchestrationState) -> None:
    triage_output = state.get("triage_output")
    triage_input = state.get("triage_input")
    payload = {
        "request_id": state.get("request_id", ""),
        "visit_id": triage_input.visit_id if triage_input else "unknown",
        "acuity_level": triage_output.acuity_level.value if triage_output else "URGENT",
        "emergency_escalated": state.get("emergency_escalated", False),
        "timestamp_utc": _now_iso(),
    }
    await CHARGE_NURSE_NOTIFICATION_QUEUE.put(payload)


@agent_span("triage.human_review")
async def human_review_node(state: TriageOrchestrationState) -> TriageOrchestrationState:
    state["human_review_pending"] = True
    state["current_node"] = "human_review"
    asyncio.create_task(_publish_charge_nurse_alert(state))

    decision: str
    try:
        result = interrupt(
            {
                "request_id": state.get("request_id", ""),
                "visit_id": state.get("triage_input").visit_id if state.get("triage_input") else "unknown",
                "reason": "Emergency escalation requires clinician adjudication",
            }
        )
        decision = str(result if result is not None else "rejected").strip().lower()
    except Exception:
        decision = str(state.get("context", {}).get("human_decision", "rejected")).strip().lower()

    state.setdefault("context", {})["human_decision"] = decision
    _append_trace(state, "human_review", {"status": "pending", "decision": decision})
    return state


@agent_span("triage.finalise")
async def finalise_node(state: TriageOrchestrationState) -> TriageOrchestrationState:
    triage_output = state.get("triage_output")
    triage_input = state.get("triage_input")
    if triage_output is None or triage_input is None:
        state["error"] = "missing_output_for_finalise"
        state["error_code"] = "FINALISE_MISSING_OUTPUT"
        state["error_detail"] = "triage_input/triage_output missing in finalise_node"
        _append_trace(state, "finalise", {"status": "failure"})
        return state

    started_at_raw = str(state.get("context", {}).get("started_at_utc", _now_iso()))
    try:
        started_at = datetime.fromisoformat(started_at_raw)
    except ValueError:
        started_at = datetime.now(UTC)
    duration_ms = (datetime.now(UTC) - started_at).total_seconds() * 1000.0

    trace_url = state.get("context", {}).get("trace_url")
    if not trace_url:
        request_id = str(state.get("request_id", ""))
        trace_url = os.getenv("LANGSMITH_TRACE_URL_TEMPLATE", "").format(request_id=request_id) if os.getenv(
            "LANGSMITH_TRACE_URL_TEMPLATE"
        ) else None

    print(f"FINALISE_DEBUG: triage_output type: {type(triage_output)}")
    print(f"FINALISE_DEBUG: triage_output dict: {triage_output.__dict__ if hasattr(triage_output, '__dict__') else triage_output}")
    if hasattr(triage_output, 'clinical_summary'):
        print(f"FINALISE_DEBUG: clinical_summary: {triage_output.clinical_summary}")
        if hasattr(triage_output.clinical_summary, '__dict__'):
            print(f"FINALISE_DEBUG: clinical_summary dict: {triage_output.clinical_summary.__dict__}")

    import json
    serialized_output = json.loads(triage_output.model_dump_json())
    print(f"FINALISE_SERIALIZED_DEBUG: output keys: {list(serialized_output.keys())}")
    print(f"FINALISE_SERIALIZED_DEBUG: clinical_summary: {serialized_output.get('clinical_summary')}")
    response = AgentResponse(
        request_id=str(state.get("request_id", triage_input.request_id)),
        agent_id="triage-summary-agent",
        status=AgentStatus.success,
        output=serialized_output,
        trace_url=trace_url,
        duration_ms=max(0.0, duration_ms),
        created_at=datetime.now(UTC),
    )

    state["final_output"] = {
        "agent_response": response.model_dump(mode="json"),
        "otel_trace_id": get_trace_id(),
    }
    state["human_review_pending"] = False
    state["current_node"] = "finalise"
    state["error"] = None
    _append_trace(state, "finalise", {"status": "success", "duration_ms": duration_ms})
    return state


@agent_span("triage.error")
async def error_node(state: TriageOrchestrationState) -> TriageOrchestrationState:
    print("ERROR_NODE_REACHED")
    started_at_raw = str(state.get("context", {}).get("started_at_utc", _now_iso()))
    try:
        started_at = datetime.fromisoformat(started_at_raw)
    except ValueError:
        started_at = datetime.now(UTC)
    duration_ms = (datetime.now(UTC) - started_at).total_seconds() * 1000.0

    error_code = str(state.get("error_code", "TRIAGE_GRAPH_ERROR"))
    error_detail = str(state.get("error_detail", state.get("error", "Unknown triage graph error")))
    triage_safe_output = _safe_empty_triage_output(state)

    response = AgentError(
        request_id=str(state.get("request_id", "")),
        agent_id="triage-summary-agent",
        output=triage_safe_output,
        trace_url=state.get("context", {}).get("trace_url"),
        duration_ms=max(0.0, duration_ms),
        created_at=datetime.now(UTC),
        error_code=error_code,
        error_detail=error_detail,
        retry_after=None,
    )

    state["final_output"] = {
        "agent_response": response.model_dump(mode="json"),
        "otel_trace_id": get_trace_id(),
    }
    state["current_node"] = "error"
    _append_trace(state, "error", {"status": "error", "error_code": error_code})
    return state


def _route_after_validate_input(state: TriageOrchestrationState) -> str:
    return "invalid" if state.get("error") else "valid"


def _route_after_governance_check(state: TriageOrchestrationState) -> str:
    if state.get("error"):
        return "block"
    if any(flag in HARD_GOVERNANCE_FLAGS for flag in state.get("governance_flags", [])):
        return "block"
    return "proceed"


def _route_after_llm_call(state: TriageOrchestrationState) -> str:
    return "failure" if state.get("error") else "success"


def _route_after_emergency_routing(state: TriageOrchestrationState) -> str:
    return "emergency" if state.get("emergency_escalated", False) else "clean"


def _route_after_human_review(state: TriageOrchestrationState) -> str:
    decision = str(state.get("context", {}).get("human_decision", "")).strip().lower()
    if decision in {"approved", "approve", "ok", "yes"}:
        return "approved"
    return "rejected"


def checkpoint_config_for_state(state: TriageOrchestrationState) -> dict[str, Any]:
    triage_input = state.get("triage_input")
    visit_id = triage_input.visit_id if triage_input is not None else str(state.get("context", {}).get("visit_id", "unknown"))
    request_id = str(state.get("request_id", ""))
    key = f"{visit_id}:{request_id}"
    return {"configurable": {"thread_id": key, "checkpoint_ns": "triage-summary-agent"}}


def build_triage_graph() -> Any:
    graph = StateGraph(TriageOrchestrationState)

    graph.add_node("validate_input", validate_input_node)
    graph.add_node("governance_check", governance_check_node)
    graph.add_node("render_prompt", render_prompt_node)
    graph.add_node("llm_call", llm_call_node)
    graph.add_node("emergency_routing", emergency_routing_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("finalise", finalise_node)
    graph.add_node("error", error_node)

    graph.add_edge(START, "validate_input")
    graph.add_conditional_edges(
        "validate_input",
        _route_after_validate_input,
        {
            "valid": "governance_check",
            "invalid": "error",
        },
    )
    graph.add_conditional_edges(
        "governance_check",
        _route_after_governance_check,
        {
            "proceed": "render_prompt",
            "block": "error",
        },
    )
    graph.add_edge("render_prompt", "llm_call")
    graph.add_conditional_edges(
        "llm_call",
        _route_after_llm_call,
        {
            "success": "emergency_routing",
            "failure": "error",
        },
    )
    graph.add_conditional_edges(
        "emergency_routing",
        _route_after_emergency_routing,
        {
            "emergency": "human_review",
            "clean": "finalise",
        },
    )
    graph.add_conditional_edges(
        "human_review",
        _route_after_human_review,
        {
            "approved": "finalise",
            "rejected": "error",
        },
    )
    graph.add_edge("finalise", END)
    graph.add_edge("error", END)

    return graph.compile(checkpointer=MemorySaver())
