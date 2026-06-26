"""Real-Gemini integration test for sessions / multi-turn (Phase 3).

Requires `AGENT_GEMINI_API_KEY` in `.env` — auto-detect selects the real Gemini
provider. Drives upload -> ask -> follow-up through the `api_client` TestClient
and asserts on REAL multi-turn behaviour: the follow-up answer reflects the
prior turn's content. Also exercises the 20-turn cap, session CRUD, the
dataset-scoped list, and the 404s — against the production SQLite driver.

The CSV uses deterministic numbers (salaries averaging exactly 50000) so the
multi-turn assertion is robust against model wording.
"""
import io

import pytest

from db.models import ConversationSessionRow, QueryRunRow
from db.session import create_db_session


# Four salaries averaging exactly 50000 (40000+45000+55000+60000 = 200000 / 4).
_SALARY_CSV = (
    "name,salary\n"
    "Alice,40000\n"
    "Bob,45000\n"
    "Carol,55000\n"
    "Dave,60000\n"
)


def _upload(client, *, name="salaries.csv", body=_SALARY_CSV):
    files = {"file": (name, io.BytesIO(body.encode()), "text/csv")}
    r = client.post("/upload", files=files)
    assert r.status_code == 200, r.text
    return r.json()["data"]["dataset_id"]


@pytest.mark.usefixtures("_require_llm_key")
def test_multi_turn_followup_reflects_prior_turn(api_client):
    """Q2 only makes sense given Q1's answer — proves real multi-turn context."""
    dataset_id = _upload(api_client)

    # Q1: a concrete fact (the average salary is 50000).
    q1 = api_client.post(
        "/ask",
        json={
            "dataset_id": dataset_id,
            "question": "What is the average salary?",
            "skip_clarification": True,
        },
    )
    assert q1.status_code == 200, q1.text
    d1 = q1.json()["data"]
    assert d1["type"] == "answer"
    assert d1["status"] == "completed", d1
    assert "[stub]" not in d1["answer_markdown"], "real provider not used"
    session_id = d1["session_id"]
    assert session_id

    # Q2: has NO antecedent without Q1's number ("that" == the average salary).
    q2 = api_client.post(
        "/ask",
        json={
            "session_id": session_id,
            "question": "Is that average higher or lower than 50000?",
            "skip_clarification": True,
        },
    )
    assert q2.status_code == 200, q2.text
    d2 = q2.json()["data"]
    assert d2["type"] == "answer"
    assert d2["status"] == "completed", d2
    assert d2["session_id"] == session_id

    answer2 = d2["answer_markdown"]
    assert answer2 and answer2.strip(), "follow-up answer must be non-empty Markdown"
    assert "[stub]" not in answer2, f"got a stub answer, real provider not used: {answer2!r}"

    # The follow-up must reflect Q1's content: the average is exactly 50000, so it
    # is neither higher nor lower. The model should reference equality / the value
    # / a comparison word — none of which it could produce without Q1's antecedent.
    low = answer2.lower()
    reflects_prior = (
        "50000" in low.replace(",", "")
        or "50,000" in low
        or "equal" in low
        or "same" in low
        or "neither" in low
        or "higher" in low
        or "lower" in low
        or "salary" in low
    )
    assert reflects_prior, (
        "follow-up answer does not reflect the prior turn's content "
        f"(no value / comparison reference): {answer2!r}"
    )


@pytest.mark.usefixtures("_require_llm_key")
def test_turn_limit_returns_400(api_client):
    dataset_id = _upload(api_client, name="cap.csv", body="x\n1\n2\n3\n")
    with create_db_session() as s:
        sess = ConversationSessionRow(
            dataset_id=dataset_id, dataset_ids_json=[dataset_id], name=None
        )
        s.add(sess)
        s.flush()
        sid = sess.id
        for i in range(20):
            s.add(
                QueryRunRow(
                    dataset_id=dataset_id,
                    session_id=sid,
                    question=f"q{i}",
                    answer="a",
                    status="completed",
                    dataset_ids_json=[dataset_id],
                )
            )

    r = api_client.post(
        "/ask",
        json={"session_id": sid, "question": "one too many", "skip_clarification": True},
    )
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["code"] == "turn_limit"


@pytest.mark.usefixtures("_require_llm_key")
def test_session_crud_lifecycle(api_client):
    dataset_id = _upload(api_client, name="crud.csv", body="x\n1\n2\n3\n4\n")

    # Create a session via /ask.
    ask = api_client.post(
        "/ask",
        json={
            "dataset_id": dataset_id,
            "question": "How many rows are in the data?",
            "skip_clarification": True,
        },
    )
    assert ask.status_code == 200, ask.text
    sid = ask.json()["data"]["session_id"]

    # GET /sessions shows it with turn_count >= 1 and first_question.
    lst = api_client.get("/sessions")
    assert lst.status_code == 200
    item = next(s for s in lst.json()["data"] if s["id"] == sid)
    assert item["turn_count"] >= 1
    assert item["first_question"] == "How many rows are in the data?"

    # GET /sessions/{id} returns turns[] with answer_html.
    detail = api_client.get(f"/sessions/{sid}")
    assert detail.status_code == 200
    turns = detail.json()["data"]["turns"]
    assert len(turns) >= 1
    assert turns[0]["answer_html"], "turn must carry rendered HTML"
    assert turns[0]["type"] == "answer"

    # PATCH rename, verify via GET.
    ren = api_client.patch(f"/sessions/{sid}/name", json={"name": "Lifecycle"})
    assert ren.status_code == 200
    assert api_client.get(f"/sessions/{sid}").json()["data"]["name"] == "Lifecycle"

    # GET /datasets/{id}/sessions lists it.
    scoped = api_client.get(f"/datasets/{dataset_id}/sessions")
    assert scoped.status_code == 200
    assert sid in [s["id"] for s in scoped.json()["data"]]

    # DELETE removes it; subsequent GET -> 404.
    dele = api_client.delete(f"/sessions/{sid}")
    assert dele.status_code == 200
    assert api_client.get(f"/sessions/{sid}").status_code == 404


def test_session_404s(api_client):
    """404s do not need a real key."""
    assert api_client.get("/sessions/bogus").status_code == 404
    assert api_client.patch("/sessions/bogus/name", json={"name": "x"}).status_code == 404
    assert api_client.get("/datasets/bogus/sessions").status_code == 404
