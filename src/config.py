from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    analyst_db_path: str = "data/analyst.duckdb"
    analyst_llm_provider: str = "stub"
    analyst_llm_model: str = "gemini-2.5-flash"
    analyst_host: str = "0.0.0.0"
    analyst_port: int = 8001

    @property
    def resolved_llm_provider(self) -> str:
        return self.analyst_llm_provider.split("#")[0].strip()

    @property
    def is_stub(self) -> bool:
        return self.resolved_llm_provider == "stub"


settings = Settings()
