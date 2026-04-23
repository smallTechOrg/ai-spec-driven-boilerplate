import google.generativeai as genai


class GeminiProvider:
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise RuntimeError("BLOGFORGE_GEMINI_API_KEY is required when BLOGFORGE_LLM_PROVIDER=gemini")
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)

    def generate(self, prompt: str) -> str:
        response = self._model.generate_content(prompt)
        return (response.text or "").strip()
