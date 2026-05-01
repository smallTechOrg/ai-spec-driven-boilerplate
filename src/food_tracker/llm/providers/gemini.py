import json
import structlog

import google.generativeai as genai

from food_tracker.domain import NutritionResult
from food_tracker.llm.providers.base import LLMProvider

log = structlog.get_logger()

_PROMPT = """\
Analyse the food in this photo and return ONLY a JSON object — no prose, no markdown, \
no code fences — with exactly these keys:

{
  "food_name": "<string: name of the food or dish>",
  "calories_kcal": <number: estimated total calories>,
  "protein_g": <number: estimated protein in grams>,
  "carbs_g": <number: estimated carbohydrates in grams>,
  "fat_g": <number: estimated fat in grams>
}

If you cannot identify food in the image, return:
{"food_name":"unknown","calories_kcal":0,"protein_g":0,"carbs_g":0,"fat_g":0}
"""


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str) -> None:
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model_name)
        self._model_name = model_name

    def analyse_food(self, image_bytes: bytes, image_filename: str) -> NutritionResult:
        log.info("gemini_request", model=self._model_name, filename=image_filename)

        # Determine MIME type from filename extension
        ext = image_filename.rsplit(".", 1)[-1].lower() if "." in image_filename else "jpeg"
        mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "heic": "image/heic"}
        mime_type = mime_map.get(ext, "image/jpeg")

        response = self._model.generate_content(
            [{"mime_type": mime_type, "data": image_bytes}, _PROMPT]
        )
        raw = response.text.strip()
        log.info("gemini_response_raw", preview=raw[:120])

        data = json.loads(raw)
        return NutritionResult(
            food_name=data["food_name"],
            calories_kcal=float(data["calories_kcal"]),
            protein_g=float(data["protein_g"]),
            carbs_g=float(data["carbs_g"]),
            fat_g=float(data["fat_g"]),
            provider="gemini",
        )
