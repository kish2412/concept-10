from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Concept 10 API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str

    secret_key: str = "change_me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    log_level: str = "INFO"
    tenant_auth_log_success: bool = False
    agentic_enabled: bool = False
    agentic_service_base_url: str | None = None
    agentic_service_token: str | None = None
    agentic_service_role: str = "nurse"
    agentic_service_timeout_seconds: int = 20
    llm_provider: str = "none"
    llm_model: str = "none"
    openai_api_key: str | None = None
    openai_base_url: str | None = None

    frontend_origins: list[str] = []


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
