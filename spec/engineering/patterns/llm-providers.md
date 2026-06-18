# Pattern: Model Layer — Providers, Stubs & Routing

**Canonical home for layer 1 (Model)** of the stack
([`../agentic-architecture.md`](../agentic-architecture.md)). Provider selection, stubs, model routing,
and the model-call features every agent uses. Model identifiers themselves live in
[`../tech-stack.md`](../tech-stack.md) § Models — not here.

---

## Model layer essentials

- **Model routing** — don't send every call to one model. Route by task difficulty: cheap/fast
  (`claude-haiku-4-5`) for classification, extraction, routing; the default (`claude-sonnet-4-6`) for
  the main loop; the strong model (`claude-opus-4-8`) for hard reasoning and as the eval judge. Make the
  routing explicit in the LLM client, configurable via env.
- **Structured outputs** — when a node needs typed data, use the provider's structured-output / tool-use
  mode and parse into a Pydantic model — never regex over free text.
- **Prompt caching** — keep the stable prefix (system prompt + tool descriptions) byte-stable so it
  stays cached across turns; this is what makes resending context every turn affordable (see
  [`memory-and-context.md`](memory-and-context.md) § Window management).
- **Extended thinking** — enable for genuinely hard reasoning steps; it trades latency/tokens for
  quality. Don't enable it blanket — it's per-call, on the hard nodes.
- **Errors** — every model call has error handling, retries with backoff on transient failures, and a
  fatal-vs-recoverable boundary the loop can act on ([`react-agent.md`](react-agent.md)).

All of the above sit behind the `LLMClient` wrapper (`project-layout.md` Rule 7) — nodes never call a
provider SDK directly.

---

## 1. `provider=auto` by default

Resolve to the real provider when the API key env var is set, otherwise to the stub. **Setting the key
is the only step the user should need** — never require flipping a second flag on top of the key.
Encapsulate this in a `resolved_llm_provider` property on `Settings` (real when key set, stub
otherwise).

## 2. Stub outputs branch on explicit node tags, not prose

Each pipeline node injects a unique tag (`<node:plan>`, `<node:draft>`, `<node:title>`, …) into its
prompt, and the stub matches on those tags. Matching on words that also appear in the prompt body
cross-contaminates — e.g. a draft prompt containing "expand this outline" must not trigger the stub's
"outline" branch and emit bullets where a draft belongs.

## 3. Stub outputs are shaped like the real thing

Whatever the real node would produce, the stub produces in the same shape — prose nodes return
paragraphs/headings, not a bare bullet list; a data node returns a plausible table, etc. Offline demos
must be believable, because every page is clearly labelled as stub mode (rule 4) and users still judge
the shape.

## 4. The UI shows a visible stub-mode banner

Every rendered page shows a banner when the resolved provider is `stub`. Inject `llm_provider` into
every template context. Silent stubs that look like real output are a bug — users will report "it
didn't work."

## 5. Tolerate dirty `.env` values

`pydantic-settings` does **not** strip inline comments. A `.env` line like
`APP_LLM_PROVIDER=stub   # stub | gemini` arrives as the literal string `"stub   # stub | gemini"`.
Strip inline `#` comments and surrounding whitespace yourself before comparing enum-like env values
(`provider`, `mode`, …) — do it in the `resolved_*` property, never trust the raw field.

---

## Testing stub mode — `setenv("KEY", "")`, not `delenv`

To simulate "no API key set" in a test, set the var to an empty string; do not delete it:

```python
# CORRECT — empty string overrides the .env placeholder
monkeypatch.setenv("APP_ANTHROPIC_API_KEY", "")

# WRONG — pydantic-settings falls back to the .env file value ("your-key-here" → truthy → real provider)
monkeypatch.delenv("APP_ANTHROPIC_API_KEY", raising=False)
```

**Why:** `pydantic-settings` reads from both the process environment and the `.env` file. `delenv`
removes the key from the process environment, but pydantic-settings then falls back to the `.env`
file, whose placeholder (`your-api-key-here`) is a non-empty string — so `resolved_llm_provider`
returns the real provider and the test fails unexpectedly. An empty string overrides the file value
and is correctly treated as stub mode.
