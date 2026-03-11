from __future__ import annotations

import re
from typing import Any

from core.governance.audit_log import GovernanceAuditLog

try:
    from guardrails.validator_base import Validator, register_validator  # type: ignore
    from guardrails.validators import FailResult, PassResult  # type: ignore
except Exception:  # pragma: no cover
    class Validator:  # type: ignore[override]
        rail_alias: str = ""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__()

    def register_validator(name: str, data_type: str):  # type: ignore[misc]
        def _decorator(cls):
            cls.rail_alias = name
            cls.rail_data_type = data_type
            return cls

        return _decorator

    class PassResult:  # type: ignore[override]
        def __init__(self, validated_output: Any = None, metadata: dict[str, Any] | None = None) -> None:
            self.validated_output = validated_output
            self.metadata = metadata or {}

    class FailResult(Exception):  # type: ignore[override]
        def __init__(self, error_message: str, fix_value: Any | None = None) -> None:
            super().__init__(error_message)
            self.error_message = error_message
            self.fix_value = fix_value


def _result_pass(value: Any, metadata: dict[str, Any] | None = None) -> Any:
    try:
        return PassResult(validated_output=value, metadata=metadata or {})
    except TypeError:
        return PassResult(value)  # type: ignore[misc]


def _result_fail(message: str, fix_value: Any | None = None) -> Any:
    try:
        return FailResult(error_message=message, fix_value=fix_value)
    except TypeError:
        return FailResult(message)


@register_validator(name="DisclaimerPresenceGuard", data_type="object")
class DisclaimerPresenceGuard(Validator):
    """Ensures triage output contains a non-empty disclaimer field."""

    def validate(self, value: Any, metadata: dict[str, Any] | None = None) -> Any:
        if not isinstance(value, dict):
            return _result_fail("Output must be an object for DisclaimerPresenceGuard.")

        disclaimer = value.get("disclaimer")
        if not isinstance(disclaimer, str) or not disclaimer.strip():
            return _result_fail("Missing or empty output.disclaimer field.")

        return _result_pass(value)


@register_validator(name="DiagnosisLanguageGuard", data_type="object")
class DiagnosisLanguageGuard(Validator):
    """Soft warning guard for diagnosis-like assertions in clinical text."""

    PATTERNS = [
        re.compile(r"\bdiagnosed with\b", re.IGNORECASE),
        re.compile(r"\bconfirms?\b", re.IGNORECASE),
        re.compile(r"\bdefinitive\b", re.IGNORECASE),
        re.compile(r"\byou have\b", re.IGNORECASE),
        re.compile(r"\bpatient has\s+[a-zA-Z][a-zA-Z\-\s]{2,}\b", re.IGNORECASE),
    ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.audit = GovernanceAuditLog()

    def validate(self, value: Any, metadata: dict[str, Any] | None = None) -> Any:
        payload_text = str(value)
        hit_pattern = ""
        for pattern in self.PATTERNS:
            if pattern.search(payload_text):
                hit_pattern = pattern.pattern
                break

        if hit_pattern:
            request_id = ""
            if isinstance(metadata, dict):
                request_id = str(metadata.get("request_id", ""))
            self.audit.append(
                request_id=request_id,
                validator_name="DiagnosisLanguageGuard",
                result="warn",
                details={
                    "reason": "Potential diagnosis-like language detected in model output.",
                    "pattern": hit_pattern,
                },
            )
            return _result_pass(value, metadata={"warning": "diagnosis_language_detected"})

        return _result_pass(value)


@register_validator(name="ConfidenceRangeGuard", data_type="object")
class ConfidenceRangeGuard(Validator):
    """Validates confidence fields are in range and model_confidence is non-zero."""

    def validate(self, value: Any, metadata: dict[str, Any] | None = None) -> Any:
        if not isinstance(value, dict):
            return _result_fail("Output must be an object for ConfidenceRangeGuard.")

        def _check_score(field: str, score: Any) -> str | None:
            if not isinstance(score, (int, float)):
                return f"{field} must be a float in [0.0, 1.0]."
            if score < 0.0 or score > 1.0:
                return f"{field}={score} is outside [0.0, 1.0]."
            return None

        model_confidence = value.get("model_confidence")
        confidence_error = _check_score("model_confidence", model_confidence)
        if confidence_error:
            return _result_fail(confidence_error)
        if float(model_confidence) <= 0.0:
            return _result_fail("model_confidence must be > 0.0.")

        emergency_flags = value.get("emergency_flags", [])
        if not isinstance(emergency_flags, list):
            return _result_fail("emergency_flags must be a list.")

        for index, item in enumerate(emergency_flags):
            if not isinstance(item, dict):
                return _result_fail(f"emergency_flags[{index}] must be an object.")
            score_error = _check_score(f"emergency_flags[{index}].confidence", item.get("confidence"))
            if score_error:
                return _result_fail(score_error)

        return _result_pass(value)


def build_validators_map() -> dict[str, Validator]:
    return {
        "DisclaimerPresenceGuard": DisclaimerPresenceGuard(),
        "DiagnosisLanguageGuard": DiagnosisLanguageGuard(),
        "ConfidenceRangeGuard": ConfidenceRangeGuard(),
    }
