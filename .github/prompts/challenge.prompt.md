---
description: "Challenge the pending change. Grill me on these changes and don't approve until I pass your test. Pose hard questions about spec authorization, failure modes, and edge cases."
agent: agent
tools: [read, search]
---

You have just finished (or are about to finish) a change. Before I accept it, challenge me:

1. Diff the working tree against `main` (or the base branch). Read every hunk.
2. For each non-trivial hunk, pose one hard question:
   - Which spec sentence authorised this change?
   - What's the failure mode I didn't handle?
   - If I revert only this hunk, does the rest still compile and pass tests?
3. Bundle all questions into a numbered list. Do **not** answer them yourself.
4. Only after I respond to every question do you mark the change approved.

Harsher is better. The point is to catch what I glossed over.
