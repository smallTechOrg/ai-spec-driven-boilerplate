import json
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./data/blogforge.db"
    gemini_api_key: str = ""
    tavily_api_key: str = ""
    images_dir: str = "./images"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    def images_path(self) -> Path:
        p = Path(self.images_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
