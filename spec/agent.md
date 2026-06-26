# Agent

> The agent design for this boilerplate's baseline. This is the **single source of truth** for the agent graph — no module may redefine the graph topology, the loop counter, or the Tool type stated here. When a build adds a capability, it fills the slots described here; it does not invent a parallel shape.

---

## Agent Architecture Pattern

| Pattern | Use when |
|---------|----------|
| **Single-agent loop** | One LLM drives a deterministic tool-call loop. No branches, no handoffs. |
| **Graph (LangGraph)** | Multi-step pipeline with conditional edges, checkpointing, or parallel nodes. |
| **Multi-agent** | Specialised sub-agents with distinct roles; orchestrator routes between them. |
| **Supervisor** | One supervisor LLM dispatches to worker agents based on task type. |
| **Human-in-the-loop** | Execution pauses at defined checkpoints for user review or approval. |

**Chosen:** **Graph (LangGraph)** — a single self-looping ReAct node (`react`) wrapped by deterministic seam nodes (input guard → memory load → react → output guard → memory write → finalize). The ReAct node is the active **capability node**; the original single-call `transform_text` node stays wired and tested as the bare **0-tool capability slot** (see Nodes). This composition draws on the reusable catalogue in [`harness/patterns/agentic-ai.md`](../harness/patterns/agentic-ai.md): pattern **5** (Tool Use), **8** (Memory Management), **10** (MCP), **16** (Resource-Aware Optimization), **17** (Reasoning / ReAct), **18** (Guardrails), **19** (Evaluation & Monitoring).

---

## LLM Provider & Model

Per-node routing — the `react` node routes by logical **task**; the seam nodes (guards, memory) make no LLM call.

| Node | Calls LLM? | Route (task) | Default model | Rationale |
|------|-----------|--------------|---------------|-----------|
| `react` (act phase) | yes | `tools` | provider default | Tool-use loop — Sonnet-class is the sweet spot |
| `react` (hard reasoning) | yes | `reason` | provider default | Escalate only the hard step (Opus-class) |
| `transform_text` (0-tool slot) | yes | — (uses default model) | provider default | The bare capability slot |
| `guard_input`, `guard_output`, `load_memory`, `write_memory`, `finalize`, `handle_error` | no | — | — | Deterministic seam nodes |

**Routing rule:** the three logical tasks — `classify`, `tools`, `reason` — map to concrete model IDs **in `.env`/settings only**, never hardcoded in `src/`. A blank route falls back to the provider's default model. See **Routing** below.

**Cost tiers (priced on the API-reported model, so routed cost stays correct on every provider):**

| Provider | Model | $/M in | $/M out |
|----------|-------|--------|---------|
| Anthropic | Haiku 4.5 (`claude-haiku-4-5`) | 1.00 | 5.00 |
| Anthropic | Sonnet 4.6 (`claude-sonnet-4-6`) | 3.00 | 15.00 |
| Anthropic | Opus 4.8 (`claude-opus-4-8`) | 5.00 | 25.00 |
| Gemini | 2.5 Flash (`gemini-2.5-flash`) | 0.15 | 0.60 |
| Gemini | 2.5 Pro (`gemini-2.5-pro`) | 1.25 | 10.00 |

**Provider extensibility:** the baseline ships two working providers — **Anthropic** and **Gemini** — behind a `BaseProvider` ABC (`call_model(prompt, *, system, model, tools) -> LLMResponse`). Adding a third (e.g. **OpenRouter**, whose OpenAI-compatible API fronts many models behind one key, or any **other** provider) is a documented ~15-minute extension: implement `BaseProvider`, add its key to settings, add its cost tiers. The product runtime stays provider-agnostic; the workshop teaches the extension point rather than shipping every provider.

**Fallback behaviour:** the LLM call is wrapped with retry + exponential backoff on rate-limit/transient errors; a hard failure sets `state["error"]` and routes to `handle_error` (no offline stub on the gate path — tests call the real API with keys from `.env`).

**Prompt strategy:** system/user split; the `react` node sends the tool schemas via the provider's native tool-calling (`tools=` for Anthropic, function declarations for Gemini); the loop replays `tool_result` blocks until the model stops calling tools.

---

## Tools & Tool Calling

**ONE Tool type. ONE registry. ONE schema method.** This is locked — MCP tools, the example tool, and any build's tools are all the same `BaseTool` subtype in the same registry.

- `src/tools/base.py` → `BaseTool(ABC)`:
  ```python
  class BaseTool(ABC):
      name: str
      description: str
      input_schema: dict          # JSON Schema for the tool's arguments
      requires_confirmation: bool = False   # least-privilege flag (guardrails reads this)

      @abstractmethod
      def run(self, **kwargs) -> str: ...
  ```
- `src/tools/registry.py` → `ToolRegistry`:
  - `register(tool: BaseTool)` — add a tool (local, builtin, or MCP-sourced).
  - `schemas_for(provider: str) -> list[dict]` — the **single** method that emits the provider-shaped tool list (`anthropic` → `tools=` blocks; `gemini` → function declarations). No `anthropic_schemas()` / `gemini_schemas()` aliases.
  - `dispatch(name, args) -> str` — looks up the tool, validates args, calls `run()`, **never raises**. On any failure it returns the JSON **error envelope**:
    ```json
    {"ok": false, "code": "TOOL_ERROR", "hint": "human-readable recovery hint"}
    ```

| Tool name | Description | Inputs | Output | Side-effects |
|-----------|-------------|--------|--------|--------------|
| `calculator` | Evaluate an arithmetic expression | `{expression: str}` | result string | none |
| `mcp_*` (per server) | Tools discovered from a configured MCP server | per remote schema | string | per remote tool |

**Tool selection strategy:** LLM choice — the model decides which tool to call from the schemas the registry emits.

**Tool failure handling:** global — `dispatch()` catches every exception into the error envelope; the envelope text is fed back to the model as the `tool_result`, so the loop can recover or abort. A tool with `requires_confirmation=True` returns a `CONFIRMATION_REQUIRED` envelope (refuse-by-default; the interactive approval UX is a labelled slot).

---

## Agent State

The single merged `AgentState`. **Cross-cutting Definition of Done:** `iterations` is the **only** loop counter — owned and incremented by the `react` node, seeded `0` in the runner, read by the budget meter. There is **no** `step` field and **no** second cap.

```python
class AgentState(TypedDict, total=False):
    # Identity
    run_id: str                          # set at initialisation
    conversation_id: str                 # set at init; keys session memory (memory phase)

    # Input
    input_text: str                      # from the trigger

    # ReAct loop (tools phase)
    messages: list[dict]                 # running provider-shaped message history
    tool_calls: list[dict]               # pending tool calls from the last model turn
    iterations: int                      # THE loop counter — incremented by react, capped by budget

    # Memory (memory phase)
    memory_context: str                  # session transcript injected into the prompt (fenced)
    session_turns: list[dict]            # this conversation's prior turns

    # Output
    output_text: str                     # final answer

    # Observability — wired by default
    tokens_in: int                       # cumulative input tokens across all LLM calls
    tokens_out: int                      # cumulative output tokens
    cost_usd: float                      # cumulative cost across all LLM calls
    latency_ms: float                    # total run wall-clock time (set by runner)
    model: str                           # last model used (or primary model)
    node_trace: list[NodeTrace]          # [{node, duration_ms}, ...] in execution order

    # Control
    error: str | None                    # set by any node on fatal failure
    guard_code: str | None               # machine-readable guard verdict (guardrails phase)
    status: str                          # "pending" | "completed" | "failed"
```

All fields are `total=False` and additive — later phases add their fields without breaking earlier ones.

---

## Nodes / Steps

Every node brackets `_enter` / `_exit` (per-node duration → `node_trace`), catches its own exceptions, sets `state["error"]` on a fatal failure, and accumulates cumulative `tokens_in/out` + `cost_usd`. The `_load_prompt` helper takes a **filename** (`transform.md`, `react.md`, `judge.md`) — this is the one intentional change to the otherwise-frozen helper.

### `react` (active capability node)
**Reads:** `input_text`, `messages`, `tool_calls`, `iterations`, `memory_context`.
**Writes:** `messages`, `tool_calls`, `output_text`, `iterations`, cumulative tokens/cost.
**LLM call:** yes — sends the registry's `schemas_for(provider)`; on a tool-use response, dispatches each call via the registry, appends the `tool_result`, and self-loops; on a plain response, sets `output_text` and exits the loop.
**Behaviour:** the think→act→observe loop. Self-loops while the model returns tool calls and `iterations < react_max_steps`; the budget meter (guardrails phase) can cut it off on cost/token caps.

### `transform_text` (0-tool capability slot — kept, not rewritten)
**Reads:** `input_text`. **Writes:** `output_text`, tokens/cost. **LLM call:** yes (single call, no tools).
**Behaviour:** the bare single-call capability. Wired in the graph and tested, but **not on the composed entry path** — it is the labelled "switch the capability node" teaching slot. CLAUDE.md's "do not change `transform_text`" contract holds: it is extended-by-addition, never repurposed.

### `guard_input` / `guard_output` (guardrails phase)
Deterministic (length/pattern) checks; on a violation set `guard_code` + `error` and route to `handle_error`. No LLM call.

### `load_memory` / `write_memory` (memory phase)
`load_memory` reads the session transcript for `conversation_id` into `memory_context` (fenced as untrusted); `write_memory` appends this turn. No LLM call.

### `finalize` / `handle_error`
`finalize` sets `status="completed"`. `handle_error` sets `status="failed"`, logs with `run_id`, terminates.

---

## Graph / Flow Topology

**The ONE composed chain — owned here, assembled once in `src/graph/agent.py`.** No module calls `set_entry_point` or repoints edges independently.

```
START
  │
  ▼
guard_input ──(error)──► handle_error ──► END
  │ (ok)
  ▼
load_memory
  │
  ▼
react ◄─────────────┐
  │  │ (tool_calls and iterations < react_max_steps)
  │  └──────────────┘  (self-loop: act → observe)
  ├──(error / budget exceeded)──► handle_error ──► END
  │ (done)
  ▼
guard_output ──(error)──► handle_error ──► END
  │ (ok)
  ▼
write_memory ──► finalize ──► END

[transform_text]  ── wired + tested, NOT on this path; the labelled 0-tool slot
```

**Conditional edges:**

| Source node | Condition | Target |
|-------------|-----------|--------|
| `guard_input` | `state["error"]` set | `handle_error` |
| `guard_input` | ok | `load_memory` |
| `react` | `tool_calls` and `iterations < react_max_steps` | `react` (self-loop) |
| `react` | `error` or budget exceeded | `handle_error` |
| `react` | done (no tool calls) | `guard_output` |
| `guard_output` | `state["error"]` set | `handle_error` |
| `guard_output` | ok | `write_memory` |

---

## Memory & Context

Four flavours from the reference model. **Only session memory is wired on the green path**; the rest are present + unit-tested **labelled slots** (interfaces defined for a build to fill).

| Flavour | Mechanism | Status |
|---------|-----------|--------|
| **Short-term** | `AgentState` (within a run) | wired (always) |
| **Session** | cross-turn transcript keyed by `conversation_id`, in a SQLite table | **wired** (the one live flavour) |
| **Long-term (episodic)** | lexical recall over past runs (`src/memory/episodic.py`) | **labelled slot** — unit-tested, not in `build_context` |
| **Semantic (facts/profile)** | `FactRow` + `upsert_fact` (`src/memory/semantic.py`) | **labelled slot** — unit-tested, not in `build_context` |

**Failure-mode mitigations (reference model):** *forgetting* → cap + summarise overflow (labelled TODO in the memory module); *contradicting* → pin facts to the semantic store and retrieve before output (slot); *poisoning* → **session/retrieved text is fenced as untrusted** in `build_context` (shipped full — never stored as raw tool output that can steer later turns).

**Context-window management:** session transcript is injected fenced; episodic/semantic retrieval (the swap point is `retrieval._lexical_score`) is the labelled extension for embedding-backed recall.

---

## Human-in-the-Loop Checkpoints

| Checkpoint | What is shown | Expected action | Default |
|------------|---------------|-----------------|---------|
| Tool requiring confirmation | the pending tool call (`requires_confirmation=True`) | approve / deny | **refuse-by-default** — `dispatch()` returns a `CONFIRMATION_REQUIRED` envelope; the interactive approval round-trip is a labelled slot |

---

## Guardrails

Input/output guards run as graph nodes; a hard per-run budget is enforced **inside the react loop**.

| Guard | Where | What |
|-------|-------|------|
| **Input guard** | `guard_input` node | max input length; blocked-pattern / jailbreak check (short, editable pattern list — a labelled teaching slot). Violation → `guard_code` + clean `failed`, **before any LLM spend**. |
| **Output guard** | `guard_output` node | schema/content validation, PII scan before `finalize`. |
| **Budget meter** | inside `react` | `react_max_steps` (loop-of-death cap, reads `iterations`), `max_cost_usd_per_run`, `max_tokens_per_run`. Exceeding any → surfaced error, never a crash. |
| **Content-trust fence** | `wrap_untrusted` in `build_context` | retrieved/tool-result text is fenced as hostile — shipped full. |
| **Least-privilege** | `BaseTool.requires_confirmation` | refuse-by-default rule (above). |

`guard_code` is surfaced on its **own** `RunRow.guard_code` column → `RunResponse.guard_code` (not stuffed into `error_message`).

---

## MCP

Consume an external MCP server (the "USB-C for tools" pattern):

- Settings entry `AGENT_MCP_SERVER_URL` (+ `AGENT_MCP_SERVER_NAME`, optional `AGENT_MCP_AUTH_TOKEN`).
- `src/tools/mcp.py` → `MCPClient.list_tools()` returns `BaseTool` instances registered into the **same** `ToolRegistry`; `server_param()` returns the connector shape `{type: "url", url, name}` (+ `authorization_token` when set), or `None` when the URL is unset.
- The **network hop is a labelled WORKSHOP STUB** (echoes); the **wiring is real and tested**: settings → adapter → registry → provider `tools=` / `mcp_servers=`. Flipping the env var makes `mcp_echo` appear in the tool list with zero node changes.

---

## Routing

Three logical tasks → model IDs from settings:

| Task | Setting | Use |
|------|---------|-----|
| `classify` | `AGENT_MODEL_CLASSIFY` | cheap/fast classification (Haiku-class) |
| `tools` | `AGENT_MODEL_TOOLS` | the tool-use loop (Sonnet-class) |
| `reason` | `AGENT_MODEL_REASON` | hard reasoning steps (Opus-class) |

`get_router().route(task)` returns the configured ID, or `None` (→ provider default) when blank. IDs live only in `.env`/settings; the owner supplies the concrete tier IDs for their chosen provider.

---

## Error Handling & Recovery

**Node-level:** each node catches its own exceptions; a fatal error sets `state["error"]` (and `guard_code` for guard violations) and routes to `handle_error`.

**Graph-level (`handle_error`):** reads `state.error` / `run_id`; sets run `status="failed"`, persists `error_message` (+ `guard_code`); logs with `run_id`; terminates.

**Resume / retry:** none in the baseline — the runner is a single synchronous `.invoke`. (LangGraph `SqliteSaver` checkpointing is noted as an alternative in the session-memory docstring; the baseline uses a transcript table in the same SQLite file for legibility.)

**Partial failure:** a failed non-critical step (e.g. a tool error) is fed back to the loop as an error envelope so the agent can recover; only fatal node errors abort.

---

## Observability

Every agent built from this skeleton has the following signals wired by default.

| Signal | What | Where |
|--------|------|-------|
| **Node trace** | `node.start` / `node.end` with `run_id`, `node`, `duration_ms` | structlog JSON → stdout |
| **LLM calls** | `llm.call`: `tokens_in`, `tokens_out`, `cost_usd`, `model` | structlog JSON → stdout |
| **Run outcome** | `run.complete` / `run.failed`: status, total `latency_ms`, cumulative tokens + cost | structlog JSON → stdout |
| **Persisted run record** | `tokens_in/out`, `cost_usd`, `latency_ms`, `model`, `node_trace`, `guard_code` | SQLite `runs` table |
| **API surface** | all of the above on `GET /runs/{run_id}` | FastAPI response |

**Evals (no-eval-no-launch):** a versioned eval set + an LLM-as-judge regression score is **required** before launch — shipped as its own build phase (`evals/`, `make eval`).

**Additional tracing (optional):** `LANGSMITH_API_KEY` in `.env` enables LangSmith traces — no code change required.

---

## Concurrency Model

- **Run isolation:** one run per `.invoke`; `run_id`-scoped DB rows. No shared mutable state across runs.
- **Parallel nodes within a run:** none — the graph is sequential with one self-loop.
- **Checkpointing:** none in the baseline (single synchronous runner). Session continuity is a transcript table, not a LangGraph checkpointer.

---

## Graph Assembly (`src/graph/agent.py`)

```python
graph = StateGraph(AgentState)

# Seam nodes + the active capability node + the bare slot
graph.add_node("guard_input", guard_input)
graph.add_node("load_memory", load_memory)
graph.add_node("react", react)
graph.add_node("guard_output", guard_output)
graph.add_node("write_memory", write_memory)
graph.add_node("finalize", finalize)
graph.add_node("handle_error", handle_error)
graph.add_node("transform_text", transform_text)   # 0-tool slot — wired, tested, off-path

graph.set_entry_point("guard_input")

graph.add_conditional_edges("guard_input",
    lambda s: "handle_error" if s.get("error") else "load_memory")
graph.add_edge("load_memory", "react")
graph.add_conditional_edges("react", after_react,   # self-loop | handle_error | guard_output
    {"react": "react", "handle_error": "handle_error", "guard_output": "guard_output"})
graph.add_conditional_edges("guard_output",
    lambda s: "handle_error" if s.get("error") else "write_memory")
graph.add_edge("write_memory", "finalize")
graph.add_edge("finalize", END)
graph.add_edge("handle_error", END)

compiled_graph = graph.compile()
```

> Phases build this incrementally: each new node is added to the assembly only when its phase lands, and every phase keeps the suite green because `transform_text` remains a valid, tested node throughout.
