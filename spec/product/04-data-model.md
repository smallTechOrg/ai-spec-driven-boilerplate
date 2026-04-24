# Data Model

## Storage Technology

No persistent storage. All data is in-memory for the lifetime of a single Streamlit request. Models are defined as Pydantic `BaseModel` classes.

## Entities

### Entity: Place

Represents a single tourist attraction or landmark in the city.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | str | yes | Name of the place |
| description | str | yes | 2–3 sentence description |
| tips | str | yes | Opening hours and/or practical visitor tip |

### Entity: Dish

Represents a local food recommendation for the city.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | str | yes | Name of the dish |
| description | str | yes | Brief description of the dish |

### Entity: ItineraryResponse

Top-level response returned by the LLM client.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| city | str | yes | City name echoed back |
| places | list[Place] | yes | Exactly 3 places |
| dish | Dish | yes | 1 local dish |

### Relationships

`ItineraryResponse` contains exactly 3 `Place` objects and exactly 1 `Dish` object.

## Data Lifecycle

Data is created on each LLM call and discarded when the Streamlit session renders the result. Nothing is persisted.

## Sensitive Data

`GOOGLE_API_KEY` is a secret. It is loaded from environment variables via Pydantic `BaseSettings` and never logged or rendered in the UI. It must not appear in `pyproject.toml`, source files, or any committed file. See `spec/engineering/secret-hygiene.md`.
