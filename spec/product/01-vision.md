# Vision

## What This Agent Does

The Travel Itinerary Agent is a Streamlit web application that takes a city name as input and returns a short travel and food itinerary: the top 3 places to visit (each with a brief description and opening hours / practical tips) plus 1 local dish to try. It uses Google Gemini to generate the itinerary as structured data.

## Who Uses It

Anyone planning a trip to an unfamiliar city — a traveller who wants a quick starting point for what to see and eat, without spending time reading multiple travel blogs.

## Core Problem Being Solved

Planning a short city trip requires reading many sources. This agent collapses that research into a single 5-second query: enter a city, get an actionable itinerary.

## Success Criteria

- [ ] User enters a city name and receives 3 labelled places with descriptions and tips
- [ ] User receives 1 local dish with a brief description
- [ ] Response is generated in under 10 seconds on a standard internet connection
- [ ] App works offline with a visible stub banner (no API key required for dev/demo)
- [ ] Real Gemini responses are coherent and city-specific

## What This Agent Does NOT Do (Out of Scope)

- Does not book tickets, hotels, or restaurants
- Does not provide multi-day itineraries or route maps
- Does not remember previous queries (stateless)
- Does not return more than 3 places or more than 1 dish per query
- Does not validate that a city name is real

## Key Constraints

- Requires a valid `GOOGLE_API_KEY` for real responses; falls back to stub mode when absent
- Model must be configurable via `TRAVEL_LLM_MODEL` env var (default: `gemini-2.5-flash`)
- No database — agent is stateless
- Response must be parseable as structured Pydantic models

## Phases of Development

| Phase | Description | Success Gate |
|-------|-------------|--------------|
| 1 | Project scaffold + Pydantic domain models + settings | `pytest tests/unit/` passes; package imports cleanly |
| 2 | Streamlit UI + stub LLM (no API key needed) | App renders; golden-path smoke test passes offline; stub banner shown |
| 3 | Real Gemini integration | App returns real structured itinerary with valid `GOOGLE_API_KEY` |
