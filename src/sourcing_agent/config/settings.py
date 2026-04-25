from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SA_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(...)
    test_database_url: str = Field(default="")
    gemini_api_key: str = Field(default="")
    llm_model: str = Field(default="gemini-2.5-flash")
    # "auto" resolves to gemini when key is set, stub otherwise
    llm_provider: str = Field(default="auto")
    log_level: str = Field(default="INFO")

    # Scoring weights (must sum to 1.0)
    weight_price: float = Field(default=0.40)
    weight_lead_time: float = Field(default=0.35)
    weight_certs: float = Field(default=0.25)

    @property
    def resolved_llm_provider(self) -> str:
        # Strip inline comments (e.g. "auto  # auto | gemini | stub")
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


def reset_settings() -> None:
    """Reset cached settings — used in tests only."""
    global _settings
    _settings = None
