from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FOOD_TRACKER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    gemini_api_key: SecretStr | None = None
    llm_model: str = "gemini-2.5-flash"
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB
    port: int = 8001

    @field_validator("database_url")
    @classmethod
    def database_url_must_be_postgres(cls, v: str) -> str:
        if not v.startswith("postgresql"):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return v

    @property
    def provider(self) -> str:
        return "gemini" if self.gemini_api_key else "stub"


@lru_cache
def get_settings() -> Settings:
    return Settings()
