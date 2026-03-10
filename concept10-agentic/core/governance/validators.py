from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from agents.registry.loader import AgentConfig
from core.schemas.validators import SchemaValidator


@dataclass(slots=True)
class FailResult(Exception):
    error_message: str
    fix_value: Any | None = None


class PIIRedactionValidator:
    """Detect and redact common PII fields from text and JSON-like content."""

    EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
    SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    NI_RE = re.compile(r"\b(?!BG|GB|KN|NK|NT|TN|ZZ)[A-CEGHJ-PR-TW-Z]{2}\d{6}[A-D]\b", re.IGNORECASE)
    ACCOUNT_RE = re.compile(r"\b\d{8,16}\b")
    NAME_RE = re.compile(r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b")

    def __init__(self) -> None:
        self._analyzer = None
        try:
            from presidio_analyzer import AnalyzerEngine  # type: ignore

            self._analyzer = AnalyzerEngine()
        except Exception:
            self._analyzer = None

    def validate(self, value: Any) -> tuple[Any, list[str]]:
        text = self._to_text(value)
        redacted = text
        redacted_fields: list[str] = []

        if self._analyzer is not None:
            try:
                findings = self._analyzer.analyze(text=text, language="en")
                for finding in findings:
                    entity = str(getattr(finding, "entity_type", "PII"))
                    redacted_fields.append(entity)
            except Exception:
                pass

        replacements = [
            (self.EMAIL_RE, "[REDACTED_EMAIL]", "email"),
            (self.SSN_RE, "[REDACTED_SSN]", "ssn"),
            (self.NI_RE, "[REDACTED_NI]", "ni_number"),
            (self.ACCOUNT_RE, "[REDACTED_ACCOUNT]", "account_number"),
            (self.NAME_RE, "[REDACTED_NAME]", "name"),
        ]
        for regex, token, field_name in replacements:
            if regex.search(redacted):
                redacted_fields.append(field_name)
                redacted = regex.sub(token, redacted)

        return self._restore_type(value, redacted), sorted(set(redacted_fields))

    @staticmethod
    def _to_text(value: Any) -> str:
        if isinstance(value, str):
            return value
        return str(value)

    @staticmethod
    def _restore_type(original: Any, text: str) -> Any:
        if isinstance(original, str):
            return text
        if isinstance(original, dict):
            cloned = dict(original)
            cloned["_redacted_text"] = text
            return cloned
        return text


class PromptInjectionShield:
    """Blocks common prompt-injection and jailbreak patterns."""

    PATTERNS = [
        r"ignore\s+previous\s+instructions",
        r"jailbreak",
        r"role\s*:\s*system",
        r"pretend\s+you\s+are",
        r"developer\s+mode",
    ]

    def validate(self, text: str) -> bool:
        normalized = text.lower()
        for pattern in self.PATTERNS:
            if re.search(pattern, normalized):
                raise FailResult(error_message=f"Prompt injection detected: pattern '{pattern}'")
        return True


class OutputSchemaValidator:
    """Validate output payload against configured output schema."""

    def __init__(self, schema_validator: SchemaValidator | None = None) -> None:
        self.schema_validator = schema_validator or SchemaValidator()

    def validate(self, agent_config: AgentConfig, output_payload: dict[str, Any]) -> bool | FailResult:
        try:
            model = self.schema_validator.load_model(agent_config.output_schema)
            model.model_validate(output_payload)
            return True
        except Exception as exc:
            return FailResult(error_message=f"Output schema validation failed: {exc}")


class ToxicityGuard:
    """Lightweight toxicity classifier based on keywords and regex patterns."""

    TOXIC_KEYWORDS = {
        "kill",
        "hate",
        "slur",
        "stupid",
        "idiot",
        "worthless",
    }
    TOXIC_PATTERNS = [
        r"\bgo\s+die\b",
        r"\bi\s+hate\s+you\b",
        r"\byou\s+are\s+trash\b",
    ]

    def validate(self, text: str) -> bool | FailResult:
        lowered = text.lower()
        for keyword in self.TOXIC_KEYWORDS:
            if keyword in lowered:
                return FailResult(error_message=f"Toxic content detected by keyword: {keyword}")
        for pattern in self.TOXIC_PATTERNS:
            if re.search(pattern, lowered):
                return FailResult(error_message=f"Toxic content detected by pattern: {pattern}")
        return True
