# Capability: Create a Writer

**What it does:** Creates a Writer persona linked to a Voice.

**Inputs:** `name` (str), `persona` (markdown — background, expertise, quirks), `voice_id` (FK).

**Outputs:** Persisted `Writer` row.

**External calls:** Postgres only.

**Error cases:** unknown `voice_id` → 422; duplicate name → form error.

**Success criteria:** Unit test: create writer linked to voice, round-trip through repository.
