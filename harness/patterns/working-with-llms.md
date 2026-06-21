# Working with LLMs

How the harness treats the model as one swappable component behind a thin client, so the
agent is testable offline, portable across providers, and never leaks a key. This file is
referenced from [../README.md](../README.md); the stack-specific traps live in
[../rules/gotchas.md](../rules/gotchas.md).

---

## One chokepoint

Every model call goes through a single thin client (`src/integrations/llm.py`). Business
logic never calls a provider SDK directly. Swapping OpenAI → Anthropic → Gemini → stub is a
config change (`…_LLM_PROVIDER`), not a code change. This is the load-bearing rule — it is
what makes the offline gate, evals, and provider-neutrality all possible.

## Provider neutrality is a feature

Default to **stub**. Real providers are opt-in via one env var. Never default telemetry,
evals, or deploy to a specific vendor — the harness wins the senior engineer (owns the code)
and the non-coder (no account required to run the offline build) at the same time.

| Provider | Default model | SDK / package | Notes |
|----------|---------------|---------------|-------|
| stub | — | none | offline default; no key; the Phase-2 gate runs here |
| gemini | `gemini-2.5-flash` | `google-genai` (`from google import genai`) | **not** `google-generativeai` (deprecated) |
| openai | `gpt-4.1` class | `openai` | set model in config, not call sites |
| anthropic | latest Sonnet/Opus | `anthropic` | use the `claude-api` skill for current ids |

Model names are config, never hardcoded — models get deprecated (see
[gotchas.md](../rules/gotchas.md)).

## The stub is two-tier (and offline is enforced)

A single canned response is not enough to exercise a real agent. The recipe ships:

1. **TestModel-style stub** — derives a call from the *registered tool schemas* and walks
   the loop to a final answer. Robust as tools change (no hardcoded rotation to maintain).
2. **FunctionModel-style stub** — a scripted client that emits an exact sequence, for
   deterministic scenario tests.

And a **hard network kill-switch**: test `conftest.py` sets `ALLOW_MODEL_REQUESTS=False`, so
a misconfigured test *cannot* make a live call or burn a key. A green stub run proves
plumbing and tool coverage — pair it with golden-case evals (see [testing.md](../rules/testing.md))
to prove behaviour. "TestModel is not magic": coverage ≠ correctness.

## Parsing model output

- Models wrap JSON in ```` ```json ```` fences even when told not to. Strip fences before
  parsing.
- Validate the parsed shape (pydantic / a TypedDict); on a parse failure, feed the error
  back into the loop for self-correction rather than crashing.
- Keep prompts as data (a template file or a constant), not scattered f-strings — so they
  can be reviewed, diffed, and evaluated.

## Resilience

- Wrap every provider call in a timeout + bounded retry with backoff. A transient 429/503
  should degrade (retry, then a graceful error node), never crash the graph.
- Cap the agent loop (`MAX_ITERATIONS`) so a confused model can't spin forever; route the
  cap to the error node, and log turn count + tool-call count + tokens every run.

## Tracing (opt-in, vendor-neutral)

Standardise structured-log fields on the OpenTelemetry **GenAI** semantic conventions
(`gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens` /
`output_tokens`, `gen_ai.tool.name`, `gen_ai.response.finish_reasons`) so traces are
portable to Langfuse / Phoenix / Logfire with a one-line exporter swap, and double as eval
inputs. Default to console/local; a SaaS exporter is one opt-in env var. Add a redaction
flag (`TRACE_INCLUDE_SENSITIVE_DATA=false`) to honour [secret-hygiene.md](../rules/secret-hygiene.md).
See [observability.md](observability.md) for the field convention and the drift loop.
