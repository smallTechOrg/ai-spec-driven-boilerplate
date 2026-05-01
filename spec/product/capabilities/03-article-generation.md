# Capability: Article Generation

**What it does:** Takes a user-supplied topic, a selected voice, and a selected writer, then runs a LangGraph agent to generate a complete blog article draft using Google Gemini. The result is persisted as an `Article` record with `status=draft`.

**Inputs:**
- `topic` (string, required): the article subject or prompt
- `voice_id` (UUID, required): reference to an existing `Voice` record
- `writer_id` (UUID, required): reference to an existing `Writer` record

**Outputs:**
- `Article` record with `status=draft`, `content` (Markdown), `title`
- `Run` record with `status=completed`

**External calls:**
- PostgreSQL: load Voice and Writer, create Article and Run, update both on completion
- Google Gemini (`gemini-2.5-flash`): single LLM call with assembled prompt

**Error cases:**
- Gemini API key missing/invalid → Run marked `failed`, Article status unchanged
- Gemini timeout or rate limit → Run marked `failed`
- Voice or Writer not found → 404 before agent starts

**Success criteria:**
- Article draft generated and saved with `status=draft`
- Title extracted from LLM output and stored
- Generation completes in < 30 seconds on nominal network
- Run record is created and updated to `completed`
