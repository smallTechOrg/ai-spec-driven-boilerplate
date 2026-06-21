# Non-Negotiables

These rules are never optional and must survive context compression. If you can remember
only a few rules, remember these.

**Cite on override.** These rules are numbered so they can be cited. Overriding any one
requires naming its number and logging a one-line justification in the session report — an
override is a deliberate, recorded act, never a silent one.

1. **Humans own the goal.** No code is written until the spec is complete enough to act
   and the supervisor has reviewed it (with researcher, executor feasibility, reviewer
   testability). Elicit as much as needed — the loop catches the rest.

2. **Spec before code.** No change to `src/` without a backing change in `spec/`. If
   asked to build something not in the spec: stop, name the gap, spec it, get sign-off,
   then build. (See `spec-driven.md`.)

3. **Outcome is evidence.** Never claim a test passed without running it. "It should
   work" is not a result. Show the output, or say you couldn't run it. Tests run against the
   **production data driver** (never a SQLite stand-in), and a green stub run is paired with
   golden-case **evals** — coverage is not correctness.

4. **Docs must be true.** Every command in the README and docs must work exactly as
   written, from the directory stated. Test them before marking work done. A README that
   lies is worse than no README.

5. **Git discipline.** Stage specific files only — never `git add -A`. Commit and push
   are one indivisible action; a commit that is not pushed does not exist. All code
   lives on a feature branch and reaches `main` only via a reviewed PR; open the PR
   before the first feature-branch commit. (See `git-and-delivery.md`.)

6. **Steps gate green; each phase gates hard.** A user-testable increment ships in **one
   phase**, built as parallel **steps** (see `workflows/build.md` → Vocabulary).
   - A **step** is done when its fast gate (<30s) is green and the analyser sees no drift on
     handoff. Never wire a dependent step on top of a red step.
   - The **phase** is done only when the full reviewer checklist passes, evals are green,
     the tree is clean and pushed, and the session report is current. This heavy gate runs
     **once per phase**, on the converged whole — not per step.

7. **The loop must close before you stop.** Before ending any unit of work: spec ↔ src ↔
   logs reconcile (the drift check is clean), tests and evals pass, the tree is clean, the
   branch is pushed, and the session report in `logs/sessions/` is up to date.

8. **Done means the user says done.** Tests passing and reviewer sign-off are necessary
   but not sufficient. Each **phase** is complete only when the user has explicitly
   accepted it — the one user-acceptance boundary per phase. Never self-declare done.

9. **Never act irreversibly without confirmation.** Deploy, delete, send email, write to
   a production DB, force-push — any action that cannot be undone requires explicit
   approval from the user via the supervisor before proceeding. Timeout is a rejection.

10. **Blockers route to the fix workflow.** If the executor cannot resolve a blocker in
    three attempts, stop immediately, do not hack around it, and route to the fix
    workflow. The analyser diagnoses; the planner re-scopes.

11. **Collect API keys at intake, via `AskUserQuestion`.** Ask for all required API keys
    before the build begins — batched into the one consolidated `AskUserQuestion` call at
    intake (Step 2 of the researcher script), never as inline text, never mid-build. If a key
    is missing and was not collected at intake, pause and surface it via `AskUserQuestion` —
    do not continue in a degraded state without telling the user, and do not ask via inline
    text they may not notice.

12. **The live files are written continuously.** `logs/PLAN.md` is the live coordination
    file (the current-phase Step DAG + Progress Tracker + Phase Acceptance) — a single
    hardcoded path every sub-agent reads/writes. The session report in `logs/sessions/`
    is the live narrative tail (the per-run narrative + Latency Ledger). Both are kept
    current as work happens, never reconstructed after the fact.

    The session report is a live tail — write to it continuously, timestamps in three
    places only.

    The Latency Ledger is the primary artifact. **Write a ledger row the moment a stage starts**
    (Start column) — not at the end. Fill End + Dur + Dominant cost on handoff. Every ~2 minutes
    during a long sub-task (uv sync, npm install, multi-file write, test run >30s) add a note in
    the ledger's Notes column: `HH:MM:SS <what is happening>`. A reader watching the file should
    see live progress; a ledger with blank rows while work is happening is non-compliant.

    Timestamps go in exactly three places — nowhere else:
    1. **Stage header** `**Start:** HH:MM:SS` — the very first write when a stage begins.
    2. **Ledger Notes column** — `HH:MM:SS <what>` every ~2 min during long sub-tasks only.
    3. **Stage footer** `**End:** HH:MM:SS` + `**Duration:** Nm` — on handoff.

    No timestamps in decisions, trace, gate output, blockers, `src/`, `README.md`, or any project
    file. Use the host clock (`date '+%Y-%m-%d %H:%M:%S'`); never invent a time.
