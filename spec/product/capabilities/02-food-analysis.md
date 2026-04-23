# Capability: Food Analysis

## What It Does

Sends the uploaded food photo to Google Gemini Vision (or a local stub in demo mode) and parses the response into a structured nutrition result: food name, calories, protein, carbs, and fat.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|---------|
| image_bytes | bytes | Pipeline state (`FoodState.image_bytes`) | yes |
| image_filename | str | Pipeline state (`FoodState.image_filename`) | yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| food_name | str | Pipeline state |
| calories_kcal | float | Pipeline state |
| protein_g | float | Pipeline state |
| carbs_g | float | Pipeline state |
| fat_g | float | Pipeline state |
| provider | str (`"gemini"` or `"stub"`) | Pipeline state |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| Google Gemini Vision (`gemini-2.0-flash`) | Send image bytes + prompt; parse JSON response | Set `FoodState.error`, return HTTP 503 to user |
| StubProvider (offline mode) | Return hardcoded nutrition data | Never fails — always returns deterministic data |

## Business Rules

- The LLM provider is selected at startup: `gemini` when `FOOD_TRACKER_GEMINI_API_KEY` is set, `stub` otherwise
- The prompt asks Gemini to return **only** a JSON object with keys `food_name`, `calories_kcal`, `protein_g`, `carbs_g`, `fat_g` — no prose
- If the response cannot be parsed as that JSON shape, return HTTP 422 to the user
- Model name is read from `FOOD_TRACKER_LLM_MODEL` (default `gemini-2.0-flash`)

## Success Criteria

- [ ] Stub provider returns a valid `NutritionResult` with all five fields populated
- [ ] Real Gemini provider returns a sensible result for a clear food photo
- [ ] If Gemini returns unparseable JSON, HTTP 422 is returned (not 500)
