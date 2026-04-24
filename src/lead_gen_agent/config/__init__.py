from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LGA_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(...)
    test_database_url: str = Field(default="")
    gemini_api_key: str = Field(default="")
    llm_model: str = Field(default="gemini-2.5-flash")
    # Raw field — may contain inline comments from .env; use resolved_llm_provider
    llm_provider: str = Field(default="auto")
    log_level: str = Field(default="INFO")

    @property
    def resolved_llm_provider(self) -> str:
        """Strip inline comments, whitespace; resolve 'auto' based on key presence."""
        raw = self.llm_provider.split("#")[0].strip().lower()
        if raw == "auto":
            return "gemini" if self.gemini_api_key.strip() else "stub"
        return raw


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
