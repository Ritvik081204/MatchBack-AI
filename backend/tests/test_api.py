import pytest
from fastapi.testclient import TestClient

from app.ai import llm_service
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    monkeypatch.setattr(llm_service.llm, "status", lambda force=False: {"available": False})


def demo_id(client):
    return client.get("/api/matches", params={"category": "demo"}).json()["items"][0]["id"]


def test_live_and_upcoming_are_empty_with_explanation(client):
    for cat in ("live", "upcoming"):
        r = client.get("/api/matches", params={"category": cat}).json()
        assert r["total"] == 0 and r["notice"]


def test_labels_never_mix_data_kinds(client):
    assert all(m["data_kind"] == "HISTORICAL" for m in client.get("/api/matches/completed").json()["items"])
    demo = client.get("/api/matches", params={"category": "demo"}).json()["items"]
    assert demo and all(m["data_kind"] == "DEMO" and "NOT a live" in m["label"] for m in demo)


def test_demo_match_hides_result_until_end(client):
    mid = demo_id(client)
    d = client.get(f"/api/matches/{mid}").json()
    assert d["result"] is None and d["replay"]["points"]
    end = client.get(f"/api/matches/{mid}", params={"at": d["replay"]["max_seq"]}).json()
    assert end["result"]


def test_every_match_endpoint_works(client):
    mid = demo_id(client)
    for p in ("scorecard", "timeline", "statistics", "milestones", "turning-points", "ball-by-ball", "suggestions"):
        assert client.get(f"/api/matches/{mid}/{p}").status_code == 200, p
    r = client.post(f"/api/matches/{mid}/catch-up", json={"length": "quick"})
    assert r.status_code == 200 and r.json()["paragraphs"]
    assert client.post(f"/api/matches/{mid}/ask", json={"question": "Who scored the most runs?"}).json()["intent"] == "top_scorer"
    ev = next(e for e in client.get(f"/api/matches/{mid}/timeline").json()["events"] if e["type"] == "wicket")
    assert client.post(f"/api/matches/{mid}/event-explanation", json={"event_id": ev["id"]}).status_code == 200


def test_errors(client):
    assert client.get("/api/matches/does-not-exist").status_code == 404
    assert client.post(f"/api/matches/{demo_id(client)}/ask", json={"question": ""}).status_code == 422
    assert client.post(f"/api/matches/{demo_id(client)}/catch-up", json={"length": "huge"}).status_code == 422
    assert client.get("/api/matches/1550716/timeline", params={"category": "nope"}).status_code == 422
