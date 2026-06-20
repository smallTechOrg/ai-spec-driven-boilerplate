# tests/e2e/test_primary_journey.py  (pytest + playwright; agent server + next dev both up)
import urllib.request

import pytest

# Skip cleanly if pytest-playwright isn't installed, rather than aborting COLLECTION of the whole suite.
pytest.importorskip("playwright")
from playwright.sync_api import expect

UI_URL = "http://localhost:3001"


def _ui_is_up() -> bool:
    try:
        urllib.request.urlopen(UI_URL, timeout=2)
        return True
    except Exception:
        return False


def test_user_gets_a_triaged_answer(page):
    # The browser journey is the demo gate's UI half — it requires the live UI + backend (the gate starts
    # both before running it). A bare keyless `uv run pytest` with no servers up SKIPS cleanly here rather
    # than red-on-connection-refused; the gate (servers up) exercises it for real.
    if not _ui_is_up():
        pytest.skip(f"UI not reachable at {UI_URL} — run inside `make gate` (it starts the UI + backend).")
    page.goto("http://localhost:3001")
    # Non-session-scoped agent: the goal field alone carries the ticket. The deterministic classify_ticket
    # tool routes a billing ticket to category "billing", so the live answer reliably echoes that input-derived
    # symbol — a REAL expected value, not merely non-empty (gates.md check 7, interface.md § Gate).
    page.get_by_role("textbox", name="goal").fill(
        "Triage this ticket and draft a reply: I was charged twice for my subscription this month "
        "and want a refund.")
    page.get_by_role("button", name="Run").click()
    answer = page.get_by_test_id("answer")
    expect(answer).not_to_be_empty(timeout=60_000)        # post-JS DOM, after the real run completes
    expect(answer).to_contain_text("billing")             # the input-derived category — a REAL expected value
    expect(page.get_by_role("link", name="trace")).to_be_visible()   # deep-link to /traces present
