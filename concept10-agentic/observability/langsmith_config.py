from __future__ import annotations

import contextvars
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic_settings import BaseSettings, SettingsConfigDict


_CURRENT_RUN_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "langsmith_current_run_id",
    default=None,
)


class LangSmithConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    langchain_api_key: str = ""
    langchain_tracing_v2: bool = True
    langchain_endpoint: str = "https://api.smith.langchain.com"
    langchain_project: str = "default"

    @property
    def enabled(self) -> bool:
        return self.langchain_tracing_v2 and bool(self.langchain_api_key)


class TraceContext:
    """Async run lifecycle manager for LangSmith traces."""

    def __init__(
        self,
        request_id: str,
        agent_id: str,
        project: str | None = None,
        *,
        parent_run_id: str | None = None,
    ) -> None:
        self.request_id = request_id
        self.agent_id = agent_id
        self.config = LangSmithConfig()
        self.project = project or self.config.langchain_project
        self.parent_run_id = parent_run_id or _CURRENT_RUN_ID.get()
        self.run_name = f"{agent_id}::{request_id}"

        self.run_id: str | None = None
        self._client: Any | None = None
        self._token: contextvars.Token[str | None] | None = None
        self._metadata: dict[str, Any] = {}
        self._tags: list[str] = []
        self._outputs: dict[str, Any] = {}

    async def __aenter__(self) -> TraceContext:
        if not self.config.enabled:
            return self

        self._metadata.setdefault("request_id", self.request_id)
        self._metadata.setdefault("agent_id", self.agent_id)

        try:
            from langsmith import Client  # type: ignore

            self._client = Client(
                api_key=self.config.langchain_api_key,
                api_url=self.config.langchain_endpoint,
            )

            created = self._client.create_run(
                name=self.run_name,
                run_type="chain",
                inputs={"request_id": self.request_id, "agent_id": self.agent_id},
                project_name=self.project,
                parent_run_id=self._safe_uuid(self.parent_run_id),
                extra={"metadata": self._metadata},
                tags=self._tags,
            )
            self.run_id = str(getattr(created, "id", None) or created.get("id"))
            self._token = _CURRENT_RUN_ID.set(self.run_id)
        except Exception:
            self._client = None
            self.run_id = None

        return self

    async def __aexit__(self, exc_type: Any, exc: BaseException | None, _tb: Any) -> None:
        if self._token is not None:
            _CURRENT_RUN_ID.reset(self._token)

        if not self._client or not self.run_id:
            return

        try:
            update_kwargs: dict[str, Any] = {
                "run_id": self._safe_uuid(self.run_id),
                "end_time": datetime.now(UTC),
                "outputs": self._outputs or None,
                "error": str(exc) if exc else None,
                "extra": {"metadata": self._metadata},
                "tags": self._tags,
            }
            self._client.update_run(**update_kwargs)
        except Exception:
            return

    def set_metadata(self, key: str, value: Any) -> None:
        self._metadata[key] = value

    def add_tag(self, tag: str) -> None:
        if tag not in self._tags:
            self._tags.append(tag)

    def set_outputs(self, outputs: dict[str, Any]) -> None:
        self._outputs = dict(outputs)

    @staticmethod
    def _safe_uuid(value: str | UUID | None) -> UUID | None:
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except ValueError:
            return None


def get_trace_url(run_id: str | UUID) -> str | None:
    cfg = LangSmithConfig()
    value = str(run_id).strip()
    if not value:
        return None

    endpoint = cfg.langchain_endpoint.rstrip("/")
    if "api.smith.langchain.com" in endpoint:
        base = endpoint.replace("api.smith.langchain.com", "smith.langchain.com")
    else:
        base = endpoint

    return f"{base}/runs/{value}"
