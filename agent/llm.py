from langchain.chat_models import init_chat_model

from .config import get_settings


def get_model():
    s = get_settings()
    key = s.llm_api_key.get_secret_value()           # unwrap the SecretStr ONLY here — the use boundary
    if not key:
        raise RuntimeError("APP_LLM_API_KEY is required for a real run (see README / spec/tech-stack.md).")
    return init_chat_model(s.llm_model, model_provider=s.llm_provider, api_key=key)
