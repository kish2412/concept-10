from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class GovernanceAuditLog:
    """Append-only governance audit logging."""

    def __init__(self, file_path: str = "core/governance/governance_audit.jsonl") -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        *,
        request_id: str,
        validator_name: str,
        result: str,
        redacted_fields: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "request_id": request_id,
            "validator_name": validator_name,
            "result": result,
            "redacted_fields": redacted_fields or [],
            "timestamp": datetime.now(UTC).isoformat(),
            "details": details or {},
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
