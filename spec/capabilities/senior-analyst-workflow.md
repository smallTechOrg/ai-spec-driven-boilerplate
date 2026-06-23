# Capability: Senior-Analyst Workflow (DEFERRED — Phase 3)
## What It Does
For ambiguous or multi-step questions, the agent clarifies before answering (human-in-the-loop) and ends with explicit recommendations / next steps, completing the clarify → plan → query → interpret → recommend loop. Phase 1 runs the chain straight through with no clarify/recommend.
## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| question + schema context | JSON | Ask Question flow | yes |
| clarification answer | string | follow-up `POST /ask` | no |
## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| clarification prompt | string (`clarification` field) | Ask box |
| recommendations | string/list (`recommendations` field) | Result view |
## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini | Confidence check / clarify / recommend | fall back to direct answer |
## Business Rules
- Clarify only fires below a confidence threshold; otherwise the flow is unchanged.
## Success Criteria
- [ ] A vague question returns a clarifying question (Phase 3).
- [ ] A normal answer ends with concrete recommendations (Phase 3).
- [ ] Phase 1: no clarify/recommend steps run.
