# Agentic-AI Patterns

The reusable catalogue of agentic design patterns — generic engineering doctrine, not a project's design. The spec-writer picks the minimal set a project actually needs and records the concrete composition in [`spec/agent.md`](../../spec/agent.md), citing the patterns chosen here. Prefer the simplest pattern that works: do not reach for multi-agent when a single tool-use loop suffices.

---

### 1. Prompt Chaining
**What** — Decompose a task into a fixed sequence of LLM steps, each consuming the prior step's output.
**When** — Choose when the task has clear, ordered sub-steps; avoid when steps are independent (parallelize) or branch by input (route).
**Example** — Draft outline → expand each section → copy-edit the assembled document.

### 2. Routing
**What** — A classifier or router directs each input to the right specialized handler or prompt.
**When** — Choose when inputs fall into distinct categories needing different handling; avoid when one prompt handles all cases well.
**Example** — Triage a support ticket to the billing, technical, or account-management sub-agent.

### 3. Parallelization
**What** — Run independent subtasks concurrently (sectioning), or sample the same task multiple times and aggregate (voting).
**When** — Choose to cut latency on independent work or raise reliability via consensus; avoid when steps depend on each other.
**Example** — Score a document against five rubric criteria at once, then merge the scores.

### 4. Reflection
**What** — The agent critiques and revises its own output before finalizing (self-review / critic loop).
**When** — Choose for quality-sensitive output where a second pass measurably helps; avoid on simple tasks — it adds a full extra round-trip.
**Example** — Generate code, run a self-review pass for bugs and edge cases, then emit the fixed version.

### 5. Tool Use (Function Calling)
**What** — The LLM calls external tools, APIs, or functions to act in the world and fetch live data.
**When** — Choose whenever the task needs real data, side effects, or computation the model can't do reliably; avoid when the answer is fully in-context.
**Example** — Call a weather API and a calendar API to propose meeting times around clear-sky windows.

### 6. Planning
**What** — The agent generates an explicit multi-step plan before acting, then executes the steps.
**When** — Choose for complex, multi-step goals where order and dependencies matter; avoid for single-shot tasks where planning is overhead.
**Example** — "Migrate this service to v2" → produce a numbered plan, then carry out each step.

### 7. Multi-Agent Collaboration
**What** — Multiple specialized agents with distinct roles coordinate to complete a task.
**When** — Choose when roles genuinely differ and separation improves quality or isolation; avoid when one agent with tools would do — it multiplies cost and latency.
**Example** — Researcher gathers sources, writer drafts, editor critiques, in a shared workflow.

### 8. Memory Management
**What** — Maintain short-term (context window) and long-term (vector store / database) memory across turns and sessions.
**When** — Choose when the agent must recall prior context or personalize; avoid persistent memory for stateless, single-shot tasks.
**Example** — A coding assistant recalls the user's stack preferences from earlier sessions.

### 9. Learning and Adaptation
**What** — The agent improves over time from feedback, examples, or observed outcomes.
**When** — Choose when behaviour should evolve with usage and you can capture a feedback signal; avoid when fixed behaviour is required or auditable determinism matters.
**Example** — Re-rank suggestions based on which past recommendations the user accepted.

### 10. Model Context Protocol (MCP)
**What** — A standardized protocol for exposing tools, data, and context to models and agents.
**When** — Choose to integrate external tools/data through a common interface and reuse servers across agents; avoid the overhead for one bespoke in-process tool.
**MCP consumption (baseline pattern)** — the agent *consumes* an external server: a settings-driven URL → an adapter that returns the remote tools as `BaseTool` instances registered into the same `ToolRegistry` as local tools. The network hop can be a labelled stub; the wiring must be real (settings → adapter → registry → provider `tools=`/`mcp_servers=`).
**Example** — Connect the agent to a GitHub MCP server to read issues and open pull requests.

### 11. Goal Setting and Monitoring
**What** — Define explicit goals and success metrics, then track progress against them during execution.
**When** — Choose for long-running or autonomous tasks needing a stopping condition; avoid when success is a single obvious end-state.
**Example** — "Reach 90% test coverage" — the agent measures coverage after each change and continues until met.

### 12. Exception Handling and Recovery
**What** — Detect failures (tool errors, malformed output) and retry, fall back, or degrade gracefully.
**When** — Choose for any agent touching unreliable tools or external systems — i.e. nearly all production agents; rarely omit.
**How:** Wrap LLM calls with `tenacity` (`wait_exponential`, `stop_after_attempt=3`, `retry=retry_if_exception_type(RateLimitError | APIError)`). Each node catches its own exceptions and sets `state["error"]` on fatal failure — never let exceptions escape the node. The `handle_error` node persists the failure to DB and terminates the graph cleanly.
**Example** — On an API timeout, retry with exponential back-off up to 3 times, then set `state["error"]` and route to `handle_error`.

### 13. Human-in-the-Loop
**What** — Insert human approval or correction at high-stakes or low-confidence decision points.
**When** — Choose for irreversible, costly, or sensitive actions, and below a confidence threshold; avoid where it would bottleneck high-volume routine work.
**Example** — Pause for human sign-off before sending a refund over $500.

### 14. Knowledge Retrieval (RAG)
**What** — Retrieve relevant external knowledge and ground the LLM's response in it.
**When** — Choose when answers depend on a corpus larger than the context window or on fresh/proprietary facts; avoid when knowledge is small enough to keep in-prompt.
**Example** — Answer policy questions by retrieving the matching sections of the employee handbook.

### 15. Inter-Agent Communication (A2A)
**What** — Agents exchange messages and results through a defined protocol or shared channel.
**When** — Choose when multiple agents (often across boundaries) must coordinate via structured messages; avoid for in-process agents that can share state directly.
**Example** — A scheduling agent negotiates a slot with a separate calendar agent over a message protocol.

### 16. Resource-Aware Optimization
**What** — Manage cost, latency, and token budgets via model tiering, caching, and truncation.
**When** — Choose at scale or under tight latency/cost limits; avoid premature tuning before a real budget pressure appears.
**Baseline that every agent should have:** cost_usd and latency_ms tracked per run (see Pattern 19) — you cannot optimize what you don't measure.
**Routing (baseline pattern)** — map logical tasks (`classify`/`tools`/`reason`) to model IDs that live only in `.env`/settings (never hardcoded in `src/`); a blank route falls back to the provider default. Price cost on the **API-reported** model so a routed call's cost is correct on every provider.
**Example** — Route easy queries to a small model and escalate only hard ones to the large model; use prompt caching for repeated system prompts.

### 17. Reasoning Techniques
**What** — Structured reasoning strategies: chain-of-thought, ReAct, tree/graph-of-thought, self-consistency.
**When** — Choose for problems where explicit intermediate reasoning improves accuracy; avoid on simple lookups where it only burns tokens.
**ReAct loop with an iterations cap (baseline pattern)** — implement think→act→observe as a single self-looping node that increments **one** loop counter (`iterations`) and stops at a `react_max_steps` cap. That cap is the loop-of-death guard (Pattern 12) and the budget meter reads the same counter — never introduce a second step field or a second cap.
**Example** — Use ReAct (reason → act → observe) so the agent interleaves thinking with tool calls.

### 18. Guardrails / Safety Patterns
**What** — Input/output validation, content filtering, constraint enforcement, and jailbreak defense.
**When** — Choose whenever inputs are untrusted or outputs are user-facing or acted upon — effectively always in production.
**Example** — Validate the model's JSON against a schema and reject responses containing disallowed content.

### 19. Evaluation and Monitoring
**What** — Offline evals plus production observability: structured per-node traces, token/cost/latency metrics per run stored in DB and emitted as structured logs, and LLM-as-judge scoring for quality regression.
**When** — Every agent you intend to ship. Non-negotiable — a skeleton with no observability is not production-ready.
**What to capture per run:** `tokens_in`, `tokens_out`, `cost_usd`, `latency_ms`, `model`, `node_trace` (per-node duration list). Store in DB; surface in API response.
**What to capture per node:** entry timestamp, exit timestamp, duration_ms. Emit `node.start` / `node.end` structured log events with `run_id`.
**What to capture per LLM call:** prompt tokens, completion tokens, model ID, cost_usd. Emit `llm.call` structured log event.
**No-eval-no-launch (required, its own build phase):** a **versioned eval set** (a handful of fixed cases is enough) plus an **LLM-as-judge** that scores the assembled agent's answers against a **pass threshold** ships as a dedicated phase (`evals/`, runnable via `make eval` / `pytest -m eval`). This is how prompt/graph changes get regression-scored — "it ran once and looked right" is not an eval.
**Example** — Run a regression eval set on each prompt change; trace every live run for per-node latency and cost; alert when cost_usd per run exceeds a threshold.

### 20. Prioritization
**What** — The agent ranks or orders competing tasks, goals, or tool calls by importance and urgency.
**When** — Choose when more work exists than can be done at once and ordering matters; avoid when there is a single task or a fixed order.
**Example** — A task agent works the highest-impact, soonest-due item from its backlog first.

### 21. Exploration and Discovery
**What** — The agent explores an open-ended space through search and experimentation rather than a fixed path.
**When** — Choose when the solution space is unknown and must be discovered; avoid when the procedure is known — just execute it.
**Example** — A research agent branches across queries and sources to map an unfamiliar topic.

---

## Choosing patterns

- **Start simple.** The simplest capable agent is often a single tool-use loop with good prompts and guardrails — begin there and measure.
- **Add a pattern only when a concrete need appears.** Each pattern is a response to a specific failure or requirement, not a default to adopt up front.
- **Justify the expensive ones.** Multi-agent, reflection, and heavy reasoning add latency and cost; reach for them only when a simpler composition demonstrably falls short.
- **Compose deliberately.** Patterns stack (e.g. planning + tool use + reflection); keep the set minimal and the data flow between them explicit.

## Non-negotiable baseline (every agent, every build)

These are not optional patterns — they are the floor. A skeleton missing any of these is not production-ready:

| Concern | Minimum |
|---------|---------|
| **Observability** | `tokens_in`, `tokens_out`, `cost_usd`, `latency_ms`, `model`, `node_trace` captured per run; stored in DB; returned in API response; emitted as structured logs (`node.start`, `node.end`, `llm.call`, `run.complete`) |
| **Error handling** | Every node catches its own exceptions; fatal errors set `state["error"]`; `handle_error` node persists failure and terminates cleanly; LLM calls wrapped with `tenacity` retry + back-off |
| **State schema** | `AgentState` typed with all fields (identity, input, output, observability, control); no untyped `dict` passing |
| **LLM response** | Providers return a typed `LLMResponse(text, tokens_in, tokens_out, model, cost_usd)` — never bare `str`; usage metadata never discarded |
| **Tool use** | Even simple agents should use structured tool/function calling for any external action; raw string parsing of LLM output is fragile |
| **Tool registry** | ONE `BaseTool` type + ONE registry with a single `schemas_for(provider)` method that emits provider-shaped tool definitions for **every** provider the runtime supports — no per-provider method aliases. Local, builtin, and MCP tools are all the same `BaseTool` subtype in the same registry. Dispatch never raises; it returns a JSON error envelope `{ok:false, code, hint}` |
| **MCP consumption** | A config-gated external MCP server (`AGENT_MCP_SERVER_URL`) whose remote tools register into the same `ToolRegistry` as local tools. The network hop may be a labelled stub, but the wiring (settings → adapter → registry → provider `tools=`/`mcp_servers=`) must be real and tested |
| **Model routing** | Logical tasks (`classify`/`tools`/`reason`) → model IDs that live **only** in `.env`/settings, never hardcoded in `src/`; a blank route falls back to the provider default. Cost is priced on the **API-reported** model so routed cost stays correct on every provider |
| **Eval gate** | The no-eval-no-launch floor: a **versioned eval set + an LLM-as-judge regression score with a pass threshold** is required before launch, shipped as its own build phase (`evals/`, `make eval`). "It ran once and looked right" is not an eval |

The chosen composition for **this** project — which patterns, wired how — is documented in [`spec/agent.md`](../../spec/agent.md).
