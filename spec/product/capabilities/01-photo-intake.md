# Capability: Photo Intake

## What It Does

Accepts a food photo uploaded via the browser form, validates its type and size, and makes the image bytes available to the analysis pipeline.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|---------|
| photo | binary file | `multipart/form-data` POST field `photo` | yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| image_bytes | bytes | Pipeline state (`FoodState.image_bytes`) |
| image_filename | str | Pipeline state (`FoodState.image_filename`) |

## External Calls

None. This capability is pure in-process validation.

## Business Rules

- Accepted MIME types: `image/jpeg`, `image/png`, `image/heic`
- Maximum file size: 10 MB (10 × 1024 × 1024 bytes)
- If no file is provided or the file is empty: return HTTP 400
- If the file exceeds 10 MB: return HTTP 400 with a human-readable error message
- If the MIME type is not accepted: return HTTP 400

## Success Criteria

- [ ] A valid JPEG/PNG under 10 MB is accepted and its bytes are passed to the pipeline
- [ ] A missing or empty file field returns HTTP 400
- [ ] A file larger than 10 MB returns HTTP 400
