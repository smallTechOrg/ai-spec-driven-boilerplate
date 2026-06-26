# Capability: Explain the Answer in Plain English

## What It Does
Turns the small computed result into a short, plain-English answer and explanation grounded in the question and the code that produced it.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| question | string | `POST /runs` body | yes |
| generated_code | string | `answer-question` | yes |
| result_table / result_scalar | small computed result | `answer-question` | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| answer | string (short answer line) | AgentState + `RunRow.answer` |
| explanation | string (1–3 sentences) | AgentState + `RunRow.explanation` |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini (`gemini-2.5-flash`) | Render explanation from question + code + the SMALL result | set `error` → `handle_error` |

## Business Rules
- Only the already-computed **small** result is sent to the LLM — never the full dataset (constraint 1).
- The explanation must describe what the computation did and the resulting figure(s); it must not invent new numbers or perform new computation.
- The explanation is grounded in `result_table`/`result_scalar`; if the result is empty, the explanation says so plainly (e.g. "no rows matched").

## Success Criteria
- [ ] For a group-by result, the explanation references the actual top value(s) from the result table.
- [ ] The explanation contains no numbers absent from the computed result.
- [ ] An empty result yields a clear "no matching rows" style explanation rather than a fabricated figure.
