from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BLOGFORGE_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(...)
    gemini_api_key: str = Field(default="")
    llm_model: str = Field(default="gemini-2.5-flash")
    llm_provider: str = Field(default="auto")  # "auto" | "stub" | "gemini"
    log_level: str = Field(default="INFO")

    @property
    def resolved_llm_provider(self) -> str:
        """`auto` means: use gemini when a key is set, otherwise stub.
        Strips inline `#` comments and whitespace defensively — a stale .env
        with `BLOGFORGE_LLM_PROVIDER=stub   # note` would otherwise pin stub.
        """
        raw = (self.llm_provider or "").split("#", 1)[0].strip().lower()
        if raw in ("", "auto"):
            return "gemini" if self.gemini_api_key.strip() else "stub"
        return raw


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Test helper."""
    global _settings
    _settings = None
