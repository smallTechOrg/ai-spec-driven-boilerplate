from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _strip_inline_comment(value: str) -> str:
    """Strip surrounding whitespace and inline `# ...` comments.

    pydantic-settings does not strip these on its own; .env files written
    weeks ago often contain values like `auto    # auto | gemini | stub`.
    """
    if value is None:
        return ""
    stripped = value.split("#", 1)[0].strip()
    return stripped


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SOURCING_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(...)
    test_database_url: str = Field(default="")

    gemini_api_key: str = Field(default="")
    llm_model: str = Field(default="gemini-2.0-flash")
    llm_provider: str = Field(default="auto")  # auto | gemini | stub

    tavily_api_key: str = Field(default="")
    search_provider: str = Field(default="auto")  # auto | tavily | stub

    log_level: str = Field(default="INFO")
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)

    @property
    def resolved_llm_provider(self) -> str:
        choice = _strip_inline_comment(self.llm_provider).lower()
        key = _strip_inline_comment(self.gemini_api_key)
        if choice == "gemini":
            return "gemini"
        if choice == "stub":
            return "stub"
        return "gemini" if key else "stub"

    @property
    def resolved_search_provider(self) -> str:
        choice = _strip_inline_comment(self.search_provider).lower()
        key = _strip_inline_comment(self.tavily_api_key)
        if choice == "tavily":
            return "tavily"
        if choice == "stub":
            return "stub"
        return "tavily" if key else "stub"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
