"""Settings — pydantic-settings, env prefix APPNAME_.

Switching provider/model/DB is a config change here, never a code change. The LLM
defaults to a stub so a fresh copy runs offline with no API key. get_settings() is
an lru_cached singleton — the one config accessor.
"""

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
    host: str = "127.0.0.1"  # bind 0.0.0.0 in a container
    port: int = 8000

    # LLM — leave as "stub" to run offline with no API key.
    # Switch to "anthropic" and set APPNAME_ANTHROPIC_API_KEY to go live.
    llm_provider: str = "stub"  # stub | anthropic
    llm_model: str = "claude-sonnet-4-6"
    anthropic_api_key: SecretStr = SecretStr("")

    # Persistence — the relational spine (SQLite via aiosqlite).
    database_url: str = "sqlite+aiosqlite:///./appname.db"

    # DuckDB columnar event-store seam + checkpointer path live under here.
    data_dir: str = "./data"

    # CORS — a single configurable origin list (never mix "*" with explicit origins).
    cors_origins: list[str] = ["http://localhost:3000"]

    @property
    def resolved_llm_provider(self) -> str:
        return self.llm_provider.split("#")[0].strip()

    @property
    def is_stub(self) -> bool:
        return self.resolved_llm_provider == "stub"


@lru_cache
def get_settings() -> Settings:
    return Settings()
