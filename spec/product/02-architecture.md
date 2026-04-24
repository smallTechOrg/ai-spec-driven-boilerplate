# Architecture

## System Overview

A single-process Streamlit web application. The user submits a city name via the browser; the app calls Google Gemini with a structured prompt; Gemini returns a JSON-shaped response that is parsed into Pydantic models and rendered back to the user. No database, no background workers.

## Component Map

```
[Browser / Streamlit UI]
    ↓  city name
[LLMClient]
    ↓  prompt
[Google Gemini API]  ← real in Phase 3, stub in Phase 2
    ↓  JSON response
[Pydantic domain models]
    ↓  typed ItineraryResponse
[Streamlit UI renders places + dish]
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| UI (`app.py`) | Streamlit form, result rendering, stub banner |
| LLM (`llm/`) | Abstract `LLMProvider`, `StubProvider`, `GeminiProvider`, factory |
| Domain (`domain/models.py`) | Pydantic models: `Place`, `Dish`, `ItineraryResponse` |
| Config (`config/settings.py`) | Pydantic `BaseSettings`, reads `GOOGLE_API_KEY` + `TRAVEL_LLM_MODEL` |

## Data Flow

1. Trigger: User types a city name in the Streamlit text input and clicks "Get Itinerary"
2. `app.py` calls `LLMClient.get_itinerary(city)`
3. `LLMClient` builds a prompt and calls the configured provider (Stub or Gemini)
4. Provider returns a JSON string; `LLMClient` parses it into `ItineraryResponse`
5. Output: Streamlit renders 3 place cards and 1 dish card

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| Google Gemini API | Generate itinerary text | Falls back to stub banner + error message |

## Deployment Model

Local development: `uv run streamlit run src/travel_itinerary/app.py`
No cloud deployment in scope for v0.1.
