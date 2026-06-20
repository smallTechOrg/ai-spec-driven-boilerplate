from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # extra="ignore": undeclared .env keys (TEST_DATABASE_URL, CI vars) MUST NOT raise. Without it the app
    # crashes on boot the moment the environment carries one key you didn't declare.
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")
    llm_provider: str = "anthropic"
    llm_model: str = "claude-haiku-4-5"             # CHEAP tier — resolves to claude-haiku-4-5-20251001
    llm_api_key: SecretStr = SecretStr("")          # SecretStr: never logged/repr'd; read only at the use boundary
    database_url: str = "sqlite+aiosqlite:///./agent.db"
    port: int = 8001
    max_iterations: int = 6
    price_in: float = 1.0       # USD per 1M input tokens  — claude-haiku-4-5 rate (cost_usd column)
    price_out: float = 5.0      # USD per 1M output tokens — claude-haiku-4-5 rate

    # RULE 1 — strip inline `#` comments + surrounding whitespace from EVERY string env value.
    # pydantic-settings does NOT do this: `APP_LLM_API_KEY=sk-xxx # prod key` is read as the literal
    # "sk-xxx # prod key", the build stays green (no call yet), and the real run 401s. Highest-ROI fix.
    @field_validator("llm_provider", "llm_model", "database_url", mode="before")
    @classmethod
    def _strip_inline_comment(cls, v):
        if isinstance(v, str):
            # split on " #" (space-hash) so URLs with a literal '#' fragment survive; then strip whitespace
            return v.split(" #", 1)[0].strip()
        return v

    @field_validator("llm_api_key", mode="before")
    @classmethod
    def _clean_secret(cls, v):
        return v.split(" #", 1)[0].strip() if isinstance(v, str) else v


@lru_cache
def get_settings() -> Settings:                      # cached Settings singleton — the one config accessor
    return Settings()


def validate_required_config() -> None:
    """Fail LOUD at boot if config the agent can't run without is missing. One named error, not a 500 later."""
    s = get_settings()
    missing = []
    if not s.llm_api_key.get_secret_value():        # the SecretStr is empty
        missing.append("APP_LLM_API_KEY")
    if not s.llm_model:
        missing.append("APP_LLM_MODEL")
    if missing:
        raise RuntimeError(f"missing required config: {', '.join(missing)} — set them in .env (see README).")
