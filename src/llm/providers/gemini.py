from google import genai
from google.genai import types


class GeminiProvider:
    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model or self.DEFAULT_MODEL

    def call_model(self, prompt: str, *, system: str | None = None) -> str:
        config = types.GenerateContentConfig(
            system_instruction=system,
        ) if system else None
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )
        return response.text

    def call_with_tools(
        self,
        prompt: str,
        tools: list,
        *,
        system: str | None = None,
    ) -> dict | None:
        """
        Call Gemini with function calling (tool use).

        Args:
            prompt: The user message.
            tools: A list of google.genai.types.Tool objects.
            system: Optional system instruction.

        Returns:
            The first FunctionCall as a dict {"name": str, "args": dict},
            or None if the model returned plain text instead of a function call.
        """
        config = types.GenerateContentConfig(
            tools=tools,
            system_instruction=system,
        )
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )
        # Extract function call from response
        try:
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if part.function_call is not None:
                        fc = part.function_call
                        return {"name": fc.name, "args": dict(fc.args)}
        except (AttributeError, IndexError, TypeError):
            pass
        return None

    def call_json(self, prompt: str, *, system: str | None = None) -> str:
        """
        Call Gemini requesting JSON output.

        Returns the raw text (which should be valid JSON).
        Falls back gracefully: if response.text is not valid JSON, returns it as-is.
        """
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            system_instruction=system,
        )
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )
        return response.text or ""
