# Coordination Model (R1 output) — migration reference

## Recommendation
Introduce a single, well-known, hardcoded coordination file — logs/PLAN.md — as the live execution blackboard for the CURRENT phase, and keep the timestamped session report (logs/sessions/YYYY-MM-DD-HHMMSS-<branch>.md) as the narrative/latency log. spec/ becomes a clean formal multi-file product spec (vision/architecture/data-model/api/ui/agent-graph/delivery-plan) and holds NO live tracking. delivery-plan.md owns the durable PHASE roadmap (ordered phases, per-phase EARS criteria PN-ACn, dependencies); logs/PLAN.md owns the ephemeral, per-phase STEP DAG + Progress Tracker that the planner regenerates each time a phase starts. The split is: phases are the durable contract in spec/; the step-slice of the CURRENT phase is the disposable coordination artefact in logs/PLAN.md.

Why a fixed path solves the prior failure: every sub-agent is hardcoded to read/write the literal path logs/PLAN.md. There is no filename to discover, no timestamp to guess, no "which session file?" ambiguity — the path is a constant in every agent prompt exactly as "spec/features/FR-NNN.md" used to be a (single) known file. The planner truncates-and-rewrites logs/PLAN.md at the start of each phase (it is scoped to ONE phase at a time), so it never grows unbounded and never needs a version suffix.

Three-file coordination model:
- spec/delivery-plan.md — durable, formal: the ordered phase list + PN-ACn criteria + phase DAG. Survives across phases. Edited only on a real spec change.
- logs/PLAN.md — live, hardcoded path: current-phase header (which phase + its PN-ACn it is realising), the Step DAG, and the Progress Tracker. The coordination hub all parallel sub-agents read/write. Rewritten per phase.
- logs/sessions/<timestamped>.md — the narrative tail + Latency Ledger. Still timestamped (one per run, append-only history is fine here BECAUSE no parallel agent needs to find it by name for coordination — the supervisor passes its path explicitly when it spawns each agent, and the SessionStart hook surfaces the latest). Coordination state does NOT live here; only the log does.

Vocabulary reconciliation: 'iteration' is retired in favour of 'phase'. One phase = one user-testable increment (was 'iteration'); steps remain the parallel work-units inside the current phase. Non-negotiable #6/#8 update from 'the iteration gates hard / one user-acceptance boundary' to 'each phase gates hard / the phase boundary is the one user-acceptance point' (delivery-plan.md already encodes this in its Phasing Model rule 3).

## Tracking location
/Users/sai/Workspace/Code/exp1/logs/PLAN.md — a single hardcoded path (never timestamped, never suffixed). Every agent prompt references this exact literal string. The planner rewrites it whole at the start of each phase; all other agents update only their own tracker row in it. The durable phase roadmap lives separately in /Users/sai/Workspace/Code/exp1/spec/delivery-plan.md; the narrative log lives in /Users/sai/Workspace/Code/exp1/logs/sessions/<timestamped>.md.

## logs/PLAN.md structure
logs/PLAN.md has exactly these sections (everything the FR's Step Plan + Progress Tracker used to hold, scoped to the current phase):

1. Header block (3 lines, rewritten each phase):
   `# PLAN — Phase <N>: <theme>`
   `**Realising:** spec/delivery-plan.md Phase <N> criteria P<N>-AC1..P<N>-ACm`
   `**Session log:** logs/sessions/<file>` (the one back-pointer to the narrative tail; supervisor fills it when it opens the phase)
   `**Status:** planning | building | review | accepted`

2. `## Step DAG` — the planner's parallel work-unit slice of THIS phase (was FR ## Step Plan):
   table: `| # | Deliverable | Depends on | Parallel group | Gate command | Est. |`
   Step 0 = scaffold (first phase only); subsequent phases start at the first delta step.

3. `## Progress Tracker` — one row per step, every agent updates its own row on handoff (was FR ## Progress Tracker):
   table: `| Step | Status (todo→in-progress→gate-green→accepted) | Gate output (session ref) | Reviewer sign-off | Dominant cost |`
   'accepted' is set only at the phase boundary when the user accepts the phase.

4. `## Phase Acceptance` — the gate checklist result for the phase + the link back to spec/delivery-plan.md PN-ACn coverage (was implicit in the FR). Reviewer writes pass/fail here; supervisor records user acceptance here.

Nothing in this file is a formal requirement — those stay in spec/. This file is pure execution state for one phase and is safe to discard/overwrite when the next phase begins.

## Rationale
1. Separation of concerns is the whole reason for the change: a formal spec must not carry live status. Phases + criteria are durable contract (spec/delivery-plan.md); the step-slice + status of the current phase is volatile coordination state (logs/PLAN.md). Putting volatile state in spec/ would re-create exactly the clutter we are removing.

2. The FR worked as a coordination hub for ONE reason: it was a single known file every agent could open without being told its name. logs/PLAN.md preserves that one good property (single, known, no-discovery path) while dropping the bad one (it doubled as the formal spec). It is a like-for-like replacement of the FR's coordination role.

3. Per-phase scoping falls out naturally: the planner already slices 'the current phase' into a step DAG (delivery-plan.md Phasing Model). A fresh logs/PLAN.md per phase means the tracker is always exactly the steps in flight — no stale rows from phase 1 cluttering phase 3, and no unbounded growth. The durable arc is preserved in delivery-plan.md, so rewriting PLAN.md loses nothing.

4. logs/ is the Outcome layer (per CLAUDE.md's four-layer table) — execution state belongs there, not in the Intention layer (spec/). This keeps the layer boundaries clean: spec/ = what it should be, logs/ = what it does (including the live plan/status of the current run).

5. The session report stays timestamped because it is an append-only historical record — multiple runs each get their own file, which is correct for a log. It does NOT need a fixed name because no parallel agent coordinates through it: the supervisor passes its path explicitly to each spawned agent, and the SessionStart hook surfaces the latest. Coordination (find-without-being-told) and logging (per-run history) are different needs and now have different files.

CAVEAT FOUND (flag, not block): /Users/sai/Workspace/Code/exp1/.gitignore line 14 ignores all of logs/, but harness/layout.md says logs/sessions/ and logs/analysis/ are committed. They are currently NOT tracked. logs/PLAN.md is gitignored under the same rule. For coordination this is irrelevant (agents read disk within a run, not git). But if PLAN.md or the session reports are meant to be a durable committed record, .gitignore needs negation lines (!logs/sessions/, !logs/analysis/, and a decision on !logs/PLAN.md). Recommend: PLAN.md stays gitignored (it is ephemeral per-phase scratch); sessions/ + analysis/ should be un-ignored to match layout.md. This is a pre-existing inconsistency, not introduced by this design.

## Per-file edits needed

### `/Users/sai/Workspace/Code/exp1/harness/process/agents/planner.md`
Replace every 'FR ## Step Plan / ## Progress Tracker / FR is the coordination hub' reference with logs/PLAN.md. Specifically: lines 14-16 (Responsibilities) — 'Writes the authoritative Step DAG + seeds the Progress Tracker into logs/PLAN.md (the single hardcoded coordination path all sub-agents read/write); the planner REWRITES logs/PLAN.md whole at the start of each phase, scoped to the CURRENT phase only, reading its PN-ACn criteria from spec/delivery-plan.md'. Line 24 postcondition + line 33 'May write' — change target from 'the FR' to 'logs/PLAN.md (## Step DAG + ## Progress Tracker + header)'. Throughout, change 'the one iteration' vocabulary to 'the current phase'. Lines 137-148 (scope-overflow): replace the 'proposed FR / spec/ROADMAP.md' deferral mechanism with 'defer to a later phase in spec/delivery-plan.md'. Section 'Session Report Entry' (159-181): keep the latency/narrative bits in the session report, but state the Step DAG table itself is written to logs/PLAN.md, not the session report.

### `/Users/sai/Workspace/Code/exp1/harness/process/agents/executor.md`
Line 31 precondition: 'The step DAG exists in the FR' -> 'The step DAG exists in logs/PLAN.md'. Line 40 postcondition + line 46 'May write': 'this step's row in the FR ## Progress Tracker' -> 'this step's row in logs/PLAN.md ## Progress Tracker'. Line 48: 'edit any FR section other than its tracker row' -> 'edit any logs/PLAN.md section other than its own tracker row, or edit spec/ at all'. Keep the 'append Start: to the session file first' logging rule unchanged — that is the timestamped session report and stays.

### `/Users/sai/Workspace/Code/exp1/harness/process/agents/reviewer.md`
Line 46 'May write ... the sign-off cells of the FR ## Progress Tracker rows in the FR' -> 'the Reviewer-sign-off cells of logs/PLAN.md ## Progress Tracker, and the ## Phase Acceptance section of logs/PLAN.md'. Throughout, change 'the iteration gate / iteration boundary' to 'the phase gate / phase boundary'. Pre-code spec gate (52-64): point at the phased spec files (vision/delivery-plan PN-ACn) instead of 'the FR'; 'same EARS forms as the FR' -> 'the PN-ACn criteria in spec/delivery-plan.md'.

### `/Users/sai/Workspace/Code/exp1/harness/process/agents/deployer.md`
Line 32 'the relevant row in the FR ## Progress Tracker in the FR' -> 'the relevant row in logs/PLAN.md ## Progress Tracker'. Line 11 'Any FR capability ... UNVERIFIED' -> 'Any phase capability (per spec/delivery-plan.md PN-ACn) ... UNVERIFIED'.

### `/Users/sai/Workspace/Code/exp1/harness/process/agents/analyser.md`
Lines 85-95: 'Tracker integrity: every FR ## Progress Tracker row' -> 'every logs/PLAN.md ## Progress Tracker row'; 'no step in the plan is missing its tracker row' unchanged but now keyed to logs/PLAN.md. 'Plan shape (read the FR ## Step Plan DAG)' -> 'read logs/PLAN.md ## Step DAG'. Line 84 'Merge integrity: every done CR's delta was folded into the spec baseline' -> remove the CR mechanism; replace with 'Spec-edit integrity: every src/ change has a backing edit in spec/ (the phased files are edited in place — there is no CR archive step)'. Add a new check: 'Phase coverage: every PN-ACn realised by the current logs/PLAN.md header has a step that advances it; every spec/delivery-plan.md SC/PN-ACn is covered by some phase (the traceability law).' Change 'one iteration of parallel steps' -> 'one phase of parallel steps'.

### `/Users/sai/Workspace/Code/exp1/harness/process/agents/researcher.md`
Postconditions (28) + 'May write' (36): 'spec/features/ contains a complete FR' -> 'the phased spec files (vision.md, architecture.md, data-model.md, api.md, ui.md, agent-graph.md, delivery-plan.md) are filled in'. Remove the 'authors the follow-up proposed FR on a scope-split' responsibility (15-21) and the proposed-FR / spec/ROADMAP.md routing in the Intake Script (60, 70) — replace with 'deferred scope is written as later phases in spec/delivery-plan.md'. The researcher writes the durable phase roadmap into delivery-plan.md; it never touches logs/PLAN.md (that is the planner's).

### `/Users/sai/Workspace/Code/exp1/harness/process/agents/supervisor.md`
Swarm orchestration (44-78): change 'independent steps of the one iteration' -> 'independent steps of the current phase'. Scope-split gate (in Responsibilities): replace the 'proposed FR' machinery with 'defer excess to a later phase in spec/delivery-plan.md'. Add to Responsibilities: 'On opening a phase, the supervisor writes the session-log back-pointer into logs/PLAN.md's header and confirms the planner has (re)written logs/PLAN.md for this phase before dispatching any executor.' State explicitly that logs/PLAN.md is the single hardcoded coordination path passed to every sub-agent (no timestamped name to discover).

### `/Users/sai/Workspace/Code/exp1/harness/process/workflows/build.md`
Vocabulary section (11-29): rename 'iteration' to 'phase' throughout (one phase = one user-testable increment; steps are the parallel units inside it). Blackboard table (49-56): change researcher Writes to the phased spec files; planner Writes to 'logs/PLAN.md (Step DAG + seeded Progress Tracker)'; executor/reviewer/deployer Writes to 'logs/PLAN.md tracker row'. Lines 60-64: replace 'The FR is the single trackable file ... in spec/features/FR-NNN.md' with 'logs/PLAN.md is the single trackable file — a hardcoded path every sub-agent opens without being told its name. The planner rewrites it per phase; every stage updates its tracker row. The session report (timestamped) holds the narrative log + latency ledger; logs/PLAN.md holds the live plan + status; spec/delivery-plan.md holds the durable phase roadmap.' Stage 2 (90-109): planner writes the step DAG to logs/PLAN.md, not the FR. Reword the autonomous-after-one-gate framing to 'after each phase the user accepts at the phase boundary'.

### `/Users/sai/Workspace/Code/exp1/harness/process/templates/SESSION.md`
Line 5 '**FR/CR:** FR-NNN' -> '**Phase:** Phase N — <theme>'. Section 'FR reference' (22-26): rename to 'Plan reference' and change body to 'Step DAG + Progress Tracker live in logs/PLAN.md (the single hardcoded coordination path). **Plan:** logs/PLAN.md  •  **Spec:** spec/delivery-plan.md Phase N'. Progress Tracker section (55-62): REMOVE the duplicate tracker table from the session template (the tracker now lives only in logs/PLAN.md — do not duplicate it here, that re-creates two-places-for-one-fact). Keep the Latency Ledger and per-stage narrative sections — those are the session report's job.

### `/Users/sai/Workspace/Code/exp1/harness/process/templates/FR.md`
Delete this file. The FR-as-trackable-file model is gone. Its ## Step Plan + ## Progress Tracker content is superseded by logs/PLAN.md (add a new template harness/process/templates/PLAN.md with the four sections from the 'structure' field); its requirement sections are superseded by the phased spec files (vision/delivery-plan already exist with PN-ACn EARS).

### `/Users/sai/Workspace/Code/exp1/harness/process/templates/CR.md`
Delete this file. There is no CR mechanism in the new model — the phased spec IS the baseline and is edited in place; a change is a spec edit + a re-planned phase in logs/PLAN.md + a session-report note. Remove the analyser's 'unmerged CR' check accordingly (covered in the analyser.md edit above).

### `/Users/sai/Workspace/Code/exp1/harness/process/templates/PLAN.md`
CREATE this new template = the logs/PLAN.md skeleton with the four sections (Header block / ## Step DAG / ## Progress Tracker / ## Phase Acceptance) described in the 'structure' field. The planner copies it to logs/PLAN.md and fills it per phase. State at the top: 'This file is the single hardcoded coordination path. It is rewritten whole at the start of each phase and scoped to that ONE phase. It carries NO formal requirements — those live in spec/.'

### `/Users/sai/Workspace/Code/exp1/CLAUDE.md`
Lines 19/21 spec-readiness check: key off the phased spec files (e.g. 'spec/delivery-plan.md still a placeholder -> run /build; filled in -> read spec/ then proceed') not spec/features/ FR/CR. Non-negotiable bullet line 57 + the four-layer table: change 'One iteration delivers the whole requirement' to 'One phase delivers a user-testable increment, built as parallel steps; steps gate green, the phase gates hard'. Add a line under 'The four layers' or 'First actions': 'Live execution state (current-phase step DAG + progress) lives in logs/PLAN.md — the single hardcoded coordination path all sub-agents read/write.'

### `/Users/sai/Workspace/Code/exp1/harness/rules/non-negotiables.md`
Rule 6 (32-38): replace 'iteration' with 'phase' — 'Steps gate green; each PHASE gates hard. ... the phase is done only when the full reviewer checklist passes ... This heavy gate runs once per phase, on the converged whole.' Rule 8 (44-47): 'the iteration is complete only when the user accepts' -> 'each phase is complete only when the user accepts it — the one user-acceptance boundary per phase'. Add to rule 12 or a new clause: 'logs/PLAN.md is the live coordination file (current-phase plan + tracker); the session report is the live narrative tail. Both are written continuously.'

### `/Users/sai/Workspace/Code/exp1/harness/layout.md`
Repo skeleton (24-49): replace the spec/ block (features/ + rules/ + patterns/ lines 25-27) with the phased files: vision.md, architecture.md, data-model.md, api.md, ui.md, agent-graph.md, delivery-plan.md. In the logs/ line (44), add 'PLAN.md (current-phase step DAG + progress tracker — the hardcoded coordination path, ephemeral, rewritten per phase)'. Note the gitignore reconciliation: logs/ is fully gitignored today but layout.md claims sessions/ + analysis/ are committed — either un-ignore them with negation rules or correct layout.md; PLAN.md may stay ignored (ephemeral).

### `/Users/sai/Workspace/Code/exp1/.gitignore`
Line 14 'logs/' ignores everything including the supposedly-committed logs/sessions/ and logs/analysis/. Add negation lines after it if those are meant to be durable: '!logs/sessions/' and '!logs/analysis/' (and their contents). Decide logs/PLAN.md: recommend it STAYS ignored (ephemeral per-phase scratch, not a durable record). This is a pre-existing bug surfaced by, not caused by, the new model — fixing it is required if PLAN.md/sessions are to persist in git, but coordination within a run works regardless.

### `/Users/sai/Workspace/Code/exp1/.claude/agents/planner.md`
Front-matter description + body: 'Writes the step plan into the FR' -> 'Writes the step DAG + seeds the progress tracker into logs/PLAN.md (the hardcoded coordination path), rewritten per phase; reads phase criteria from spec/delivery-plan.md. Never writes src/ or spec/.'

### `/Users/sai/Workspace/Code/exp1/.claude/agents/executor.md`
Body: '... write src/ and unit tests for the current step only; update your own row in logs/PLAN.md ## Progress Tracker; never touch another executor's files or edit spec/.' (replace any implicit FR-tracker assumption with logs/PLAN.md).

### `/Users/sai/Workspace/Code/exp1/.claude/agents/reviewer.md`
Body: add 'record sign-off in logs/PLAN.md ## Progress Tracker + ## Phase Acceptance and in the session report' so the reviewer stub points at the new coordination file rather than the FR.

### `/Users/sai/Workspace/Code/exp1/.claude/agents/deployer.md`
Body: add 'record the deploy result in the session report and update your row in logs/PLAN.md ## Progress Tracker' (replaces the implicit FR-tracker reference in the canonical deployer.md).

### `/Users/sai/Workspace/Code/exp1/.claude/agents/researcher.md`
Body/description: 'authors the spec' should name the phased files (vision/architecture/data-model/api/ui/agent-graph/delivery-plan), and explicitly 'never writes logs/PLAN.md (that is the planner's coordination file)'. Remove any FR/spec/features wording.

### `/Users/sai/Workspace/Code/exp1/.claude/hooks/session-start.sh`
Optional but recommended: after surfacing the latest session report, also surface the coordination file so the supervisor sees current-phase status on resume: add a line 'echo "Current plan/tracker: logs/PLAN.md (read its Progress Tracker for where the phase stands)"' guarded by a test -f logs/PLAN.md. This reinforces the single known path without changing coordination semantics.

### `/Users/sai/Workspace/Code/exp1/spec/README.md`
Delete (per the new model there is no spec/README; the phased files are self-describing). If retained transitionally, remove the features/ and ROADMAP.md lines and the 'features/ = WHAT' governance rule, and add nothing about tracking (spec/ holds no live state).

### `/Users/sai/Workspace/Code/exp1/spec/ROADMAP.md`
Delete. Deferred/future scope now lives as later phases in spec/delivery-plan.md (its Later Phases + Explicitly Deferred sections already cover this). No proposed-FR tier.

### `/Users/sai/Workspace/Code/exp1/scripts/reset.py`
Lines 44/59-65: stop wiping spec/features/; instead reset logs/PLAN.md (delete it — ephemeral) and reset the phased spec/*.md files to their placeholder template state. Update the printed lines accordingly ('reset logs/PLAN.md (coordination scratch)', 'reset spec/*.md to placeholders').

