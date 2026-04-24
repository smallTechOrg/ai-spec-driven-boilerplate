from __future__ import annotations

import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _clean(value: str | None) -> str:
    """Strip inline `#` comments + whitespace from an env value.

    pydantic-settings does NOT strip inline comments. A .env written months ago
    with `LEADGEN_LLM_PROVIDER=stub   # stub | gemini` must not pin the wrong
    provider.
    """
    if value is None:
        return ""
    # Strip inline comment (only after whitespace, to not break urls with #)
    if "#" in value:
        head, _, _ = value.partition("#")
        value = head
    return value.strip()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LEADGEN_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(default="postgresql+psycopg2://sai@localhost:5432/lead_gen_agent")
    llm_provider: str = Field(default="auto")
    llm_model: str = Field(default="gemini-2.5-flash")
    log_level: str = Field(default="INFO")

    @property
    def resolved_llm_provider(self) -> str:
        raw = _clean(self.llm_provider).lower() or "auto"
        if raw == "auto":
            key = _clean(os.environ.get("GEMINI_API_KEY"))
            return "gemini" if key else "stub"
        return raw


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
