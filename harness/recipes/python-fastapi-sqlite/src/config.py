from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APPNAME_",
        env_file=".env",
        extra="ignore",
    )

    # App
    env: str = "development"
    host: str = "127.0.0.1"   # bind 0.0.0.0 inside a container
    port: int = 8000

    # CORS — explicit origin list, never mix "*" with named origins.
    cors_origins: list[str] = ["http://localhost:3000"]

    # LLM — leave provider as "stub" to run offline with no API key.
    # Switch to "anthropic" and set the key to go live (needs the `llm` extra).
    llm_provider: str = "stub"   # stub | anthropic
    llm_model: str = "claude-sonnet-4-6"
    anthropic_api_key: SecretStr = SecretStr("")

    # Database — local-first relational store (SQLite via aiosqlite).
    database_url: str = "sqlite+aiosqlite:///./appname.db"

    @property
    def resolved_llm_provider(self) -> str:
        return self.llm_provider.split("#")[0].strip()

    @property
    def is_stub(self) -> bool:
        return self.resolved_llm_provider == "stub"


@lru_cache
def get_settings() -> Settings:
    return Settings()
