# AI Agents Entry Point (OpenAI Codex / GitHub Copilot)

Same entry point as CLAUDE.md — read that file for full instructions.

## Quick Start

1. Read `spec/engineering/ai-agents.md` before doing anything else
2. Check if `spec/product/01-vision.md` is filled in
   - If not → do not write application code; surface the agent-builder instructions to the user
   - If yes → read the full spec manifest in CLAUDE.md before writing any code
3. Open a session report at `reports/sessions/YYYY-MM-DD-HHMMSS-[branch].md`

**Intake/approval UI:** For all user-facing questions (intake, approval), always use dynamic question UI (e.g., Copilot’s askQuestions, Claude’s UI) if available. See `.claude/agents/agent-builder.md` for the canonical rule.

## Sub-agents

Sub-agent definitions live in `.claude/agents/` as markdown files. They can be used as system prompts for any AI assistant. The agent-builder is the master orchestrator — start there for a new project.
