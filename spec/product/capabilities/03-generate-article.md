# Capability: Generate an Article

**What it does:** Given writer + topic, runs a LangGraph pipeline (plan → draft → finalize) that calls Gemini and persists the resulting Article.

**Inputs:** `writer_id` (FK), `topic` (str), `notes` (optional str).

**Outputs:** Persisted `Article` (title, body markdown, writer_id, voice_id, topic) + `AgentRun` row with status.

**External calls:** Google Gemini; Postgres.

**Error cases:** LLM error → `AgentRun` status=`failed`, error_message stored; article not created.

**Success criteria:** Phase 2 integration test runs the pipeline with a stub LLM provider, writes one Article + one AgentRun with status=`completed`, no API key needed.
