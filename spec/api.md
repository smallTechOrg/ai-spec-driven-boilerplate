# API

## API Style

REST (FastAPI). All responses follow the envelope `{ "data": <payload>, "error": <string or null> }`.

## Authentication

None — personal tool, local deployment only.

## Endpoints

### POST /datasets

Upload a CSV or Excel file. Creates a dataset record and saves the file to disk.

**Request:** `multipart/form-data`, field name `file`

**Response 200:**
```json
{
  "data": {
    "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "sales.csv",
    "columns": [
      {"name": "month", "dtype": "object"},
      {"name": "product", "dtype": "object"},
      {"name": "revenue", "dtype": "int64"}
    ],
    "row_count": 150
  },
  "error": null
}
```

**Error cases:**
| Status | Condition |
|--------|-----------|
| 422 | File extension is not .csv, .xlsx, or .xls |
| 500 | File write or pandas parse failure |

---

### POST /analyze

Run a natural-language analysis question against an uploaded dataset.

**Request body (JSON):**
```json
{
  "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
  "question": "Show me revenue by month as a bar chart"
}
```

**Response 200:**
```json
{
  "data": {
    "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
    "chart_type": "bar",
    "labels": ["Jan", "Feb", "Mar"],
    "values": [12000, 15000, 18000],
    "summary": "Revenue grew steadily from January to March, reaching a peak of $18,000 in March."
  },
  "error": null
}
```

**Error cases:**
| Status | Condition |
|--------|-----------|
| 404 | dataset_id not found in SQLite |
| 500 | Gemini API error, pandas execution error, or JSON parse failure |

---

### GET /datasets

List all uploaded datasets, newest first.

**Response 200:**
```json
{
  "data": [
    {
      "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
      "filename": "sales.csv",
      "columns": [
        {"name": "month", "dtype": "object"},
        {"name": "revenue", "dtype": "int64"}
      ],
      "row_count": 150,
      "created_at": "2026-06-28T10:30:00Z"
    }
  ],
  "error": null
}
```

---

### GET /health

Health check.

**Response 200:**
```json
{
  "data": {"status": "ok"},
  "error": null
}
```
