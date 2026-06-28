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

    # Where uploaded source files / DuckDB caches are stored (local only).
    data_dir: str = Field(default="./data/datasets")
    # Max upload size in bytes (~100 MB default).
    max_upload_bytes: int = Field(default=100 * 1024 * 1024)

    # LLM provider — auto-detected from whichever key is set if left blank
    llm_provider: str = Field(default="")   # "anthropic" | "gemini"
    # Low cost tier flash model is the default for the Local Data Analyst.
    llm_model: str = Field(default="gemini-2.5-flash")

    # Provider keys — set exactly one
    anthropic_api_key: str = Field(default="")
    gemini_api_key: str = Field(default="")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
