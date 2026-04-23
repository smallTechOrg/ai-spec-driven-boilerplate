# Capability: Define a Voice

**What it does:** Lets the user create/edit a Voice — a named bundle of tone, style, and do/don't guidelines used by writers.

**Inputs:** `name` (str), `description` (str), `guidelines` (markdown string).

**Outputs:** Persisted `Voice` row; redirect to voice list.

**External calls:** Postgres only.

**Error cases:** duplicate name → form error; missing required fields → 422.

**Success criteria:** Unit test: repository creates and reads a Voice.
