from __future__ import annotations

import contextvars
from uuid import uuid4


class RequestTracker:
    """Singleton request tracker based on ContextVar propagation."""

    _instance: RequestTracker | None = None

    def __new__(cls) -> RequestTracker:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._request_id_var = contextvars.ContextVar("request_id", default="")
            cls._instance._category_var = contextvars.ContextVar("agent_category", default="orchestrator")
        return cls._instance

    def set_request_id(self, request_id: str) -> None:
        self._request_id_var.set(str(request_id))

    def get_request_id(self) -> str:
        return self._request_id_var.get() or ""

    def set_agent_category(self, category: str) -> None:
        self._category_var.set((category or "orchestrator").strip().lower())

    def generate_request_id(self) -> str:
        category = self._category_var.get()
        prefix = self._prefix_for_category(category)
        return f"{prefix}-{uuid4()}"

    @staticmethod
    def _prefix_for_category(category: str) -> str:
        normalized = (category or "").strip().lower()
        if normalized.startswith("orch") or normalized == "orchestrator":
            return "orch"
        if normalized.startswith("util") or normalized == "utility":
            return "util"
        if normalized.startswith("spec") or normalized == "specialist":
            return "spec"
        if normalized in {"human", "human-in-loop", "hil"}:
            return "hil"
        return "agt"


request_tracker = RequestTracker()
