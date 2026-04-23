# AI Agent Rules

**These rules apply to every AI coding session in this repo — Claude Code, GitHub Copilot, Cursor, or any other AI assistant.**

Read this file completely before doing anything else.

---

## 1. Session Start Checklist

Complete all steps in order before writing any code:

- [ ] Read `spec/product/01-vision.md` — know what you're building
- [ ] Check if the spec is complete (no `<!-- FILL IN -->` markers in product spec files)
  - If incomplete: surface the agent-builder to the user; do not write application code
- [ ] If spec is complete: read the full spec manifest in `CLAUDE.md`
- [ ] Run `git status` — working tree must be clean before starting
- [ ] Open a session report: `reports/sessions/YYYY-MM-DD-HHMMSS-[branch].md`
  - Use the template in `spec/engineering/workflows/session-report.md`
- [ ] Confirm which phase you are implementing (see `spec/engineering/phases.md`)

## 2. Session Report (Mandatory)

Every session must have a report at `reports/sessions/YYYY-MM-DD-HHMMSS-[branch].md`.

Minimum required sections:
- **Goal:** What this session is trying to accomplish
- **Phase:** Which implementation phase
- **Steps completed:** Logged as you work (not reconstructed at the end)
- **Prompt log:** Every user message and a one-line summary of your action
- **Next steps:** What remains

Update the report in real time. Do not reconstruct it from memory at the end.

## 3. Spec-First Rule

**No code change without a spec backing it.**

If you are asked to implement something not in the spec:
1. Stop
2. Tell the user what spec gap you found
3. Propose adding it to the spec first
4. Wait for approval before writing code

See `spec/engineering/spec-driven.md` for full details.

## 4. Phase Discipline

**Never start phase N+1 while phase N is incomplete or failing.**

Each phase ends when:
- All code for that phase is written and committed
- All tests for that phase pass
- The qa-auditor sub-agent has signed off (or you have run the QA checklist manually)

See `spec/engineering/phases.md` for the phase definitions and gates.

## 5. Git Discipline

- Commit every logical unit of work — never let the working tree stay dirty for more than one logical change
- Push after every commit on feature branches
- Commit message format: `phase-N: [what you did]` (e.g., `phase-1: add domain models`)
- Never commit secrets (API keys, passwords, tokens)
- Never force-push without user confirmation

**Before every reply to the user:**
1. Run `git status`
2. If dirty: commit the changes
3. Confirm the working tree is clean before replying

## 6. Test Before Claiming Done

A phase is not done until tests pass. "It looks right" is not a test.

- Write tests for each capability as you implement it
- Run the full test suite before marking a phase complete
- If tests fail, fix them before moving on

## 7. Error Resilience

Every external call (API, database, LLM) must have:
- Error handling that doesn't crash the agent
- Logged failures (to file or stdout at minimum)
- Graceful degradation (the agent continues if a non-critical step fails)

## 8. No Gold-Plating

Build what the spec says, nothing more.

- No extra features "while you're in there"
- No refactoring outside the current phase scope
- No premature abstractions
- If you spot a future improvement, add it to `reports/sessions/[current].md` under "Future improvements" and keep moving

## 9. When Stuck

If requirements are unclear:
1. Stop
2. List your specific questions in the session report
3. Ask the user — do not guess

If the spec is ambiguous:
1. State the ambiguity
2. Propose an interpretation
3. Wait for confirmation before implementing

## 10. Closing a Session

Before ending a session:
- [ ] Working tree is clean (all changes committed and pushed)
- [ ] Session report is complete and up to date
- [ ] Tests pass
- [ ] `README.md` updated if project layout, setup steps, or commands changed
- [ ] Note which phase you're on and what comes next in the session report
