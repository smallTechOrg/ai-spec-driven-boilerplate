# API

## Endpoints

All endpoints are served by FastAPI.

### POST /api/runs

Create a new sourcing run and trigger the agent asynchronously.

**Request body:**
```json
{
  "project_name": "Downtown Tower Block A",
  "materials": [
    {"name": "Portland Cement", "quantity": 500, "unit": "bags"},
    {"name": "Clay Bricks", "quantity": 10000, "unit": "units"}
  ]
}
```

**Response 201:**
```json
{"run_id": "<uuid>", "status": "pending"}
```

**Errors:** 422 Unprocessable Entity if validation fails.

---

### GET /api/runs/{run_id}/status

Poll for run status.

**Response 200:**
```json
{"run_id": "<uuid>", "status": "running|completed|failed", "completed_at": null}
```

---

### GET /api/runs/{run_id}/report

Get the full recommendation report as JSON.

**Response 200:**
```json
{
  "run_id": "<uuid>",
  "project_name": "...",
  "status": "completed",
  "materials": [
    {
      "material_name": "Portland Cement",
      "quantity": 500,
      "unit": "bags",
      "recommendations": [
        {
          "rank": 1,
          "supplier_name": "...",
          "price_per_unit": 12.50,
          "currency": "USD",
          "lead_time_days": 7,
          "certifications": "ISO 9001, ISO 14001",
          "score": 0.8750
        }
      ]
    }
  ]
}
```

---

### GET /health

Health check.

**Response 200:** `{"status": "ok"}`
