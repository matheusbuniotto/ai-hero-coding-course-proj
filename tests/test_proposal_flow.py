from fastapi.testclient import TestClient

from tests.conftest import sign_in as _sign_in
from tests.fakes import FakeEmailPort


def test_propose_approve_updates_canonical_tree_end_to_end(
    client: TestClient, email_port: FakeEmailPort
) -> None:
    _sign_in(client, email_port, "walker@example.com")

    propose_response = client.post(
        "/workspace/files/propose", json={"path": "notes.md", "content": "hello"}
    )
    assert propose_response.status_code == 200
    proposal = propose_response.json()
    assert proposal["status"] == "pending"

    assert client.get("/workspace/api").json()["tree"] == []

    approve_response = client.post(f"/workspace/proposals/{proposal['id']}/approve")
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    workspace_body = client.get("/workspace/api").json()
    assert workspace_body["tree"] == ["notes.md"]

    history = client.get("/workspace/history").json()
    assert len(history) == 1
    assert history[0]["path"] == "notes.md"
    assert history[0]["status"] == "approved"


def test_propose_reject_leaves_canonical_tree_unchanged(
    client: TestClient, email_port: FakeEmailPort
) -> None:
    _sign_in(client, email_port, "walker@example.com")

    proposal = client.post(
        "/workspace/files/propose", json={"path": "notes.md", "content": "hello"}
    ).json()

    reject_response = client.post(f"/workspace/proposals/{proposal['id']}/reject")
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "rejected"

    assert client.get("/workspace/api").json()["tree"] == []
    assert client.get("/workspace/proposals").json() == []


def test_new_proposal_supersedes_pending_one_for_same_path(
    client: TestClient, email_port: FakeEmailPort
) -> None:
    _sign_in(client, email_port, "walker@example.com")

    first = client.post(
        "/workspace/files/propose", json={"path": "notes.md", "content": "v1"}
    ).json()
    second = client.post(
        "/workspace/files/propose", json={"path": "notes.md", "content": "v2"}
    ).json()

    pending = client.get("/workspace/proposals").json()
    assert [p["id"] for p in pending] == [second["id"]]

    approve_first = client.post(f"/workspace/proposals/{first['id']}/approve")
    assert approve_first.status_code == 404


def test_proposal_endpoints_require_auth(client: TestClient) -> None:
    response = client.post("/workspace/files/propose", json={"path": "notes.md", "content": "hi"})
    assert response.status_code == 401


def test_get_file_returns_canonical_content(client: TestClient, email_port: FakeEmailPort) -> None:
    _sign_in(client, email_port, "walker@example.com")
    proposal = client.post(
        "/workspace/files/propose", json={"path": "notes.md", "content": "hello"}
    ).json()
    client.post(f"/workspace/proposals/{proposal['id']}/approve")

    response = client.get("/workspace/files?path=notes.md")

    assert response.status_code == 200
    assert response.json() == {"path": "notes.md", "content": "hello"}


def test_get_file_404s_for_unknown_path(client: TestClient, email_port: FakeEmailPort) -> None:
    _sign_in(client, email_port, "walker@example.com")

    response = client.get("/workspace/files?path=nope.md")

    assert response.status_code == 404
