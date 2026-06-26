"""Offline session suite (Phase 3) — stub provider, in-memory SQLite, zero net.

Pins the stub LLM provider so `/ask` returns canned node-tagged output and never
touches the network. Exercises the session lifecycle end to end through the
`api_client` TestClient: session auto-creation on `/ask`, the session list with
`turn_count`/`first_question`, the session detail with rendered `answer_html`
turns, rename, dataset-scoped listing, delete (one / all), the 20-turn cap, and
multi-turn history assembly. It asserts envelope SHAPES and status codes — never
LLM content (stub answers are canned).
"""
import io

import pytest

from db.models import ConversationSessionRow, QueryRunRow
from db.session import create_db_session


@pytest.fixture(autouse=True)
def _force_stub_provider(monkeypatch):
    """Pin the offline stub provider regardless of any key in `.env`."""
    monkeypatch.setenv("AGENT_LLM_PROVIDER", "stub")
    import config.settings as m
    m._settings = None


_CSV = "value,label\n10,a\n20,b\n30,c\n"


def _upload_csv(client, *, name="sample.csv", body=_CSV):
    files = {"file": (name, io.BytesIO(body.encode()), "text/csv")}
    return client.post("/upload", files=files)


def _ask(client, dataset_id, question="describe it", **kw):
    payload = {"dataset_id": dataset_id, "question": question, "skip_clarification": True}
    payload.update(kw)
    return client.post("/ask", json=payload)


# --- session auto-creation on /ask ---------------------------------------


def test_ask_creates_a_session(api_client):
    up = _upload_csv(api_client)
    dataset_id = up.json()["data"]["dataset_id"]
    r = _ask(api_client, dataset_id)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["type"] == "answer"
    assert data["session_id"], "every /ask must belong to a session"
    # The new session is scoped to the resolved dataset.
    sid = data["session_id"]
    sess = api_client.get(f"/sessions/{sid}")
    assert sess.status_code == 200
    assert dataset_id in sess.json()["data"]["dataset_ids"]


def test_ask_resumes_existing_session(api_client):
    up = _upload_csv(api_client)
    dataset_id = up.json()["data"]["dataset_id"]
    first = _ask(api_client, dataset_id, question="q1").json()["data"]
    sid = first["session_id"]
    # Resume: pass session_id, no dataset -> inherits.
    second = api_client.post(
        "/ask", json={"session_id": sid, "question": "q2", "skip_clarification": True}
    )
    assert second.status_code == 200, second.text
    assert second.json()["data"]["session_id"] == sid


# --- session list --------------------------------------------------------


def test_session_list_has_turn_count_and_first_question(api_client):
    up = _upload_csv(api_client)
    dataset_id = up.json()["data"]["dataset_id"]
    _ask(api_client, dataset_id, question="how many rows?")

    r = api_client.get("/sessions")
    assert r.status_code == 200
    rows = r.json()["data"]
    assert len(rows) == 1
    item = rows[0]
    assert item["turn_count"] >= 1
    assert item["first_question"] == "how many rows?"
    assert "updated_at" in item


def test_session_list_orders_most_recent_first(api_client):
    up = _upload_csv(api_client)
    dataset_id = up.json()["data"]["dataset_id"]
    s1 = _ask(api_client, dataset_id, question="first").json()["data"]["session_id"]
    s2 = _ask(api_client, dataset_id, question="second").json()["data"]["session_id"]
    ids = [row["id"] for row in api_client.get("/sessions").json()["data"]]
    # Most recently updated (s2) comes first.
    assert ids[0] == s2
    assert s1 in ids


# --- session detail ------------------------------------------------------


def test_session_detail_returns_turns_with_html(api_client):
    up = _upload_csv(api_client)
    dataset_id = up.json()["data"]["dataset_id"]
    sid = _ask(api_client, dataset_id, question="describe it").json()["data"]["session_id"]

    r = api_client.get(f"/sessions/{sid}")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["id"] == sid
    assert isinstance(data["turns"], list)
    assert len(data["turns"]) == 1
    turn = data["turns"][0]
    assert turn["type"] == "answer"
    assert turn["run_id"]
    assert turn["question"] == "describe it"
    assert turn["answer_markdown"]  # stub answer is non-empty
    assert turn["answer_html"]  # rendered from markdown
    assert isinstance(turn["steps"], list)
    assert isinstance(turn["suggested_questions"], list)
    assert isinstance(turn["prompt_breakdown"], dict)
    assert turn["clarification_question"] is None


def test_session_detail_404_when_missing(api_client):
    r = api_client.get("/sessions/does-not-exist")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "not_found"


# --- rename --------------------------------------------------------------


def test_rename_session(api_client):
    up = _upload_csv(api_client)
    dataset_id = up.json()["data"]["dataset_id"]
    sid = _ask(api_client, dataset_id).json()["data"]["session_id"]

    r = api_client.patch(f"/sessions/{sid}/name", json={"name": "My Analysis"})
    assert r.status_code == 200
    assert r.json()["data"]["name"] == "My Analysis"
    # Persisted.
    assert api_client.get(f"/sessions/{sid}").json()["data"]["name"] == "My Analysis"


def test_rename_session_404_when_missing(api_client):
    r = api_client.patch("/sessions/ghost/name", json={"name": "x"})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "not_found"


# --- dataset-scoped listing ----------------------------------------------


def test_dataset_sessions_lists_scoped(api_client):
    up = _upload_csv(api_client)
    dataset_id = up.json()["data"]["dataset_id"]
    sid = _ask(api_client, dataset_id).json()["data"]["session_id"]

    r = api_client.get(f"/datasets/{dataset_id}/sessions")
    assert r.status_code == 200
    ids = [row["id"] for row in r.json()["data"]]
    assert sid in ids


def test_dataset_sessions_excludes_other_dataset(api_client):
    a = _upload_csv(api_client, name="a.csv")
    b = _upload_csv(api_client, name="b.csv", body="x,y\n1,2\n3,4\n")
    id_a = a.json()["data"]["dataset_id"]
    id_b = b.json()["data"]["dataset_id"]
    sid_a = _ask(api_client, id_a).json()["data"]["session_id"]

    scoped_b = api_client.get(f"/datasets/{id_b}/sessions").json()["data"]
    assert sid_a not in [row["id"] for row in scoped_b]


def test_dataset_sessions_404_when_dataset_missing(api_client):
    r = api_client.get("/datasets/ghost/sessions")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "not_found"


# --- delete --------------------------------------------------------------


def test_delete_session(api_client):
    up = _upload_csv(api_client)
    dataset_id = up.json()["data"]["dataset_id"]
    sid = _ask(api_client, dataset_id).json()["data"]["session_id"]

    r = api_client.delete(f"/sessions/{sid}")
    assert r.status_code == 200
    assert api_client.get(f"/sessions/{sid}").status_code == 404


def test_delete_session_404_when_missing(api_client):
    r = api_client.delete("/sessions/ghost")
    assert r.status_code == 404


def test_delete_all_sessions(api_client):
    up = _upload_csv(api_client)
    dataset_id = up.json()["data"]["dataset_id"]
    _ask(api_client, dataset_id, question="a")
    _ask(api_client, dataset_id, question="b")
    r = api_client.delete("/sessions")
    assert r.status_code == 200
    assert api_client.get("/sessions").json()["data"] == []


# --- 20-turn cap ---------------------------------------------------------


def test_turn_limit_blocks_21st_turn(api_client):
    up = _upload_csv(api_client)
    dataset_id = up.json()["data"]["dataset_id"]
    # Create a session and seed 20 settled turns directly.
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


def test_turn_count_under_limit_proceeds(api_client):
    up = _upload_csv(api_client)
    dataset_id = up.json()["data"]["dataset_id"]
    with create_db_session() as s:
        sess = ConversationSessionRow(
            dataset_id=dataset_id, dataset_ids_json=[dataset_id], name=None
        )
        s.add(sess)
        s.flush()
        sid = sess.id
        for i in range(19):
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
        json={"session_id": sid, "question": "the 20th", "skip_clarification": True},
    )
    assert r.status_code == 200, r.text


# --- 404s on /ask --------------------------------------------------------


def test_ask_404_when_session_missing(api_client):
    up = _upload_csv(api_client)
    dataset_id = up.json()["data"]["dataset_id"]
    r = api_client.post(
        "/ask",
        json={"session_id": "ghost", "dataset_id": dataset_id, "question": "hi", "skip_clarification": True},
    )
    assert r.status_code == 404


def test_ask_404_when_dataset_missing(api_client):
    r = api_client.post(
        "/ask", json={"dataset_id": "ghost", "question": "hi", "skip_clarification": True}
    )
    assert r.status_code == 404


def test_ask_no_datasets_uploaded(api_client):
    r = api_client.post("/ask", json={"question": "hi", "skip_clarification": True})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "no_datasets"
