from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AGENT_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(default="sqlite:///./data/agent.db")
    log_level: str = Field(default="INFO")

    # LLM provider — auto-detected from whichever key is set if left blank
    llm_provider: str = Field(default="")   # "anthropic" | "gemini"
    llm_model: str = Field(default="")      # uses provider default when blank

    # Provider keys — set exactly one
    anthropic_api_key: str = Field(default="")
    gemini_api_key: str = Field(default="")

    # LLM model overrides (per node)
    llm_model_plan: str = Field(default="gemini-2.5-flash")    # plan_analysis node
    llm_model_reason: str = Field(default="gemini-2.5-pro")    # reason_answer node

    # PostgreSQL external data source (Phase 2)
    postgres_dsn: str = Field(default="")

    # LangSmith — SDK reads LANGCHAIN_* from os.environ directly (no AGENT_ prefix).
    # These fields allow loading them from .env via pydantic-settings for reference.
    # The lifespan startup copies them into os.environ for the SDK to pick up.
    langchain_api_key: str = Field(default="")
    langchain_tracing_v2: str = Field(default="")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
