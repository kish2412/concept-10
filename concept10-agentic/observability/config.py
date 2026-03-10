from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ObservabilitySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    enable_langsmith: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = ""

    enable_otel: bool = False
    otel_service_name: str = "agent-orchestration-framework"
    otel_exporter_otlp_endpoint: str = ""
