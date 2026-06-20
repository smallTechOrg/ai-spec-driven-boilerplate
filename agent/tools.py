import json

from langchain_core.tools import tool

# ---------------------------------------------------------------------------------------------------------
# P1 — triage: classify urgency + category, then ground the reply in the support policy.
# Both are pure-compute in-process @tools (no network/DB I/O) → sync, dispatched via .invoke.
# ---------------------------------------------------------------------------------------------------------

URGENCY_LABELS = ("low", "normal", "high", "urgent")
CATEGORY_LABELS = ("billing", "technical", "account", "shipping", "general")

# Keyword signals — deterministic so the routing decision is reproducible and gate-stable. The model
# CALLS this tool (it does not classify by itself) so the urgency/category come from one auditable place.
_URGENCY_SIGNALS = {
    "urgent": ("urgent", "asap", "immediately", "emergency", "right now", "can't access",
               "cannot access", "locked out", "down", "outage", "charged twice", "double charged",
               "fraud", "unauthorized", "data loss", "security"),
    "high": ("angry", "frustrated", "unacceptable", "broken", "not working", "error",
             "failed", "refund", "cancel", "deadline", "soon", "escalate"),
    "low": ("question", "wondering", "curious", "how do i", "how to", "feature request",
            "suggestion", "no rush", "whenever"),
}
_CATEGORY_SIGNALS = {
    "billing": ("bill", "billing", "charge", "charged", "invoice", "payment", "refund",
                "subscription", "price", "pricing", "card", "receipt"),
    "technical": ("error", "bug", "crash", "not working", "broken", "fails", "failed",
                  "login", "log in", "page", "app", "website", "load", "500", "404", "timeout"),
    "account": ("account", "password", "locked out", "can't access", "cannot access",
                "email change", "username", "profile", "2fa", "verification"),
    "shipping": ("ship", "shipping", "delivery", "delivered", "tracking", "package",
                 "order", "arrive", "arrived", "return", "lost in transit"),
}


def _score(text: str, signals: dict[str, tuple]) -> dict[str, int]:
    t = text.lower()
    return {label: sum(1 for kw in kws if kw in t) for label, kws in signals.items()}


@tool
def classify_ticket(ticket_text: str) -> str:
    """Classify a support ticket's urgency (low/normal/high/urgent) and category
    (billing/technical/account/shipping/general). Returns a JSON object {"urgency","category","signals"}.
    Call this BEFORE drafting a reply — it is the single source of the routing decision."""
    us = _score(ticket_text, _URGENCY_SIGNALS)
    best_urgency = max(us, key=us.get)
    urgency = best_urgency if us[best_urgency] > 0 else "normal"   # default normal when no signal fires

    cs = _score(ticket_text, _CATEGORY_SIGNALS)
    best_category = max(cs, key=cs.get)
    category = best_category if cs[best_category] > 0 else "general"

    return json.dumps({
        "urgency": urgency,
        "category": category,
        "signals": {"urgency": us, "category": cs},
    })


# Small bundled support-policy corpus (in-process keyword lookup — the `search_docs` shape, NOT a RAG index).
POLICY_CORPUS = {
    "billing": "Billing & refunds: refunds are processed within 5 business days to the original payment "
               "method. We never charge before a subscription renews. Duplicate charges are reversed within "
               "3 business days once confirmed. Only an authorized billing agent can issue a refund — the "
               "assistant drafts the reply but never issues one.",
    "shipping": "Shipping: standard delivery is 3–5 business days; express is next-day for orders placed "
                "before the 2pm cutoff. A lost package is re-shipped free of charge after a 7-day trace.",
    "account": "Account & access: a locked account is unlocked via the self-service reset link, which "
               "expires after 30 minutes. Account deletion is irreversible and must be performed by the "
               "account owner from Settings — support never deletes an account on request.",
    "technical": "Technical issues: clear the cache and retry first; persistent 500 errors are investigated "
                 "within one business day. Include the error message and the time it occurred.",
    "general": "General: our support hours are 9am–6pm on business days. We aim to first-respond within "
               "one business day; urgent issues are prioritized.",
}


@tool
def search_policy(category: str) -> str:
    """Look up the company support policy for a category (billing/technical/account/shipping/general).
    Use the result to ground any timeframe or procedure in the drafted reply — never invent a policy."""
    key = (category or "").strip().lower()
    if key in POLICY_CORPUS:
        return POLICY_CORPUS[key]
    # fall back to a keyword match against the text so a free-form query still grounds
    hits = [v for k, v in POLICY_CORPUS.items() if k in key]
    return "\n".join(hits) if hits else POLICY_CORPUS["general"]


# ---------------------------------------------------------------------------------------------------------
# P2 / P3 — deterministic, journey-complete STUBS (registered + reachable; fixed contract until promoted).
# ---------------------------------------------------------------------------------------------------------

@tool
def escalate_ticket(reason: str, queue: str = "tier-2") -> str:
    """[P2 stub] Escalate a high/urgent ticket to a human queue. Returns a fixed escalation record.
    Promoted to a real router via /spec-new-capability."""
    return json.dumps({"queue": queue or "tier-2", "status": "escalated", "reason": reason})


@tool
def summarize_thread(thread: str) -> str:
    """[P3 stub] Summarize a back-and-forth ticket thread to its open question. Returns a fixed summary
    record. Promoted to a real summarizer via /spec-new-capability."""
    messages_seen = max(1, thread.count("\n\n") + 1) if thread else 0
    return json.dumps({
        "open_question": "What is the current status and next step for this request?",
        "messages_seen": messages_seen,
    })


# ---------------------------------------------------------------------------------------------------------
# Deep-Agent planning scratchpad + the termination tool.
# ---------------------------------------------------------------------------------------------------------

@tool
def write_todos(todos: list[str]) -> str:
    """Record a short ordered plan (the Deep-Agent planning scratchpad). Call before multi-step work."""
    return "Plan recorded:\n" + "\n".join(f"{i+1}. {t}" for i, t in enumerate(todos))


@tool
def finish(answer: str) -> str:
    """Return the final answer to the user and end the run. Call exactly once when done."""
    return answer


TOOLS = [classify_ticket, search_policy, escalate_ticket, summarize_thread, write_todos, finish]
TOOL_MAP = {t.name: t for t in TOOLS}
FINISH = "finish"
