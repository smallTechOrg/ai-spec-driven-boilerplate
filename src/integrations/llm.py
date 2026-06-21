import json as _json

from src.config import settings


class BaseLLMClient:
    def complete(self, prompt: str, system: str = "") -> str:
        raise NotImplementedError


class StubLLMClient(BaseLLMClient):
    def complete(self, prompt: str, system: str = "") -> str:
        # Extract only the user question line so prompt boilerplate doesn't trigger chart intent
        question_line = prompt
        for line in prompt.splitlines():
            if line.lower().startswith("user question:"):
                question_line = line
                break
        # Extract dataset name from prompt if available
        ds = "sales"
        for line in prompt.splitlines():
            if line.lower().startswith("datasets available:"):
                parts = line.split(":", 1)
                if len(parts) > 1 and parts[1].strip() not in ("", "none"):
                    ds = parts[1].strip().split(",")[0].strip()
                break
        if "plot" in question_line.lower() or "chart" in question_line.lower():
            return _json.dumps({
                "intent": "chart",
                "sql": f"SELECT product, revenue FROM {ds} LIMIT 20",
                "x_col": "product",
                "y_col": "revenue",
            })
        return _json.dumps({"intent": "table", "sql": f"SELECT * FROM {ds} LIMIT 10"})


def get_llm_client() -> BaseLLMClient:
    provider = settings.resolved_llm_provider
    if provider == "stub":
        return StubLLMClient()
    raise NotImplementedError(f"Provider {provider!r} not yet implemented")
