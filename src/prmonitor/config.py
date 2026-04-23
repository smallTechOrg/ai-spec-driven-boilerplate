from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite+aiosqlite:///./data/prmonitor.db"
    github_token: str = ""
    github_org: str = ""
    slack_webhook_url: str = ""
    stale_days: int = 3

settings = Settings()
