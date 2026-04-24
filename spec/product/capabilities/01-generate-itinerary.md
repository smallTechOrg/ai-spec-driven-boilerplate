# Capability: Generate Travel Itinerary

## Summary

Given a city name, the agent returns the top 3 places to visit and 1 local dish to try.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| city | str | yes | Name of the city (e.g., "Paris", "Tokyo") |

## Outputs

Returns an `ItineraryResponse` containing:
- `city` — the city name echoed back
- `places` — list of exactly 3 `Place` objects
- `dish` — exactly 1 `Dish` object

## Behaviour

1. User submits `city` via the Streamlit text input
2. `LLMClient.get_itinerary(city)` builds a structured prompt asking for 3 places and 1 dish as JSON
3. Provider (Stub or Gemini) returns a JSON string
4. Response is parsed into `ItineraryResponse`; parse errors surface as a UI error message
5. Result is displayed to the user

## Stub Behaviour (Phase 2)

When no `GOOGLE_API_KEY` is set, the `StubProvider` returns hardcoded JSON for any city. A yellow banner is shown in the UI.

## Acceptance Criteria

- [ ] Entering "Paris" returns 3 places each with name, description, and tips
- [ ] Entering "Paris" returns 1 dish with name and description
- [ ] Entering an empty string shows a validation warning (no LLM call made)
- [ ] When stub mode is active, banner is visible before results
- [ ] When LLM fails, error message is shown and app does not crash
