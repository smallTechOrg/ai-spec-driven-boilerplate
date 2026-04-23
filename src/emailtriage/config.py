from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite+aiosqlite:///./data/emailtriage.db"
    anthropic_api_key: str = ""
    max_emails: int = 50

settings = Settings()
