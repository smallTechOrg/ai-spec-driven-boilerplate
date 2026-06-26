"""Offline stub provider.

Auto-engages when no LLM key is configured so the whole app is usable with
zero API keys and zero network I/O. It branches **only** on the injected node
tag found in the prompt text (`<node:plan>`, `<node:select>`, ...), never on
prose keywords. The tag table is the contract in
`spec/agent.md` -> "## Stub provider node-tag branching".
"""
from __future__ import annotations

import json
import re

# Canned synthesis returned for <node:finalize> and as the wrap-up FINAL ANSWER
# for later <node:plan> calls. Kept plain so the app renders something sensible.
_FINALIZE_SUMMARY = (
    "[stub] Based on the available data, here is a best-effort summary. "
    "Set AGENT_GEMINI_API_KEY in .env for a real analysis."
)

# 1st-call action for <node:plan>: a bare pandas expression execute_action runs.
_PLAN_FIRST_ACTION = "df.describe().to_string()"

# Safe default when no recognised tag (or an unparseable plan tag) is present.
_PLAN_FALLBACK = "FINAL ANSWER: [stub] Unable to process"

# Matches a uuid-ish or token id near an `id` column header inside the schema
# block. The select prompt embeds dataset ids as `id: <value>` / `"id": "<value>"`
# lines; we grab the first plausible identifier.
_ID_PATTERNS = (
    # `"id": "abc-123"` or `id: abc-123` (json-ish / yaml-ish schema lines)
    re.compile(r'["\']?\bid["\']?\s*[:=]\s*["\']?([A-Za-z0-9][\w-]{2,})'),
    # bare uuid anywhere in the schema block, as a fallback
    re.compile(r'\b([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\b'),
)


class StubProvider:
    """Node-tag-branching offline provider. Takes no API key."""

    def __init__(self, **kwargs) -> None:  # tolerant: factory may pass model/api_key
        # Intentionally ignores api_key/model — the stub needs neither.
        pass

    def call_model(self, prompt: str, *, system: str | None = None) -> str:
        text = prompt or ""

        if "<node:finalize>" in text:
            return _FINALIZE_SUMMARY

        if "<node:select>" in text:
            return self._select(text)

        if "<node:plan>" in text:
            return self._plan(text)

        if "<node:clarify>" in text:
            return "proceed"

        if "<node:suggest>" in text:
            return "[]"

        # No recognised tag -> safe default.
        return _PLAN_FALLBACK

    # --- per-tag handlers ----------------------------------------------------

    def _select(self, text: str) -> str:
        """First dataset id from the schema block as a 1-element JSON array."""
        for pattern in _ID_PATTERNS:
            match = pattern.search(text)
            if match:
                return json.dumps([match.group(1)])
        return json.dumps([])

    def _plan(self, text: str) -> str:
        """1st call -> describe action; later call -> FINAL ANSWER.

        "Later" is inferred from the action-history transcript: every executed
        step leaves a `Result:` or `Error:` marker in the prompt. One or more
        markers means we have already run at least one action, so we wrap up.
        Successive calls differ (action then answer) so the loop terminates.
        """
        markers = self._count_markers(text)
        if markers >= 1:
            return (
                "FINAL ANSWER: [stub] Here is a best-effort summary based on the "
                "computed result above. Set AGENT_GEMINI_API_KEY in .env for a "
                "real analysis."
            )
        return _PLAN_FIRST_ACTION

    @staticmethod
    def _count_markers(text: str) -> int:
        """Count `Result:` / `Error:` markers in the action-history transcript.

        Each executed step in the assembled prompt is rendered with a
        `Result:` or `Error:` label, so the marker count is the number of
        actions already run this turn.
        """
        return len(re.findall(r'\b(?:Result|Error)\s*:', text))
