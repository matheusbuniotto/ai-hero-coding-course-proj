"""The single call the UI shell makes to find out who it is serving."""

from collections.abc import Callable

from fastapi.testclient import TestClient

from tests.conftest import sign_in
from tests.fakes import FakeEmailPort

USER = "walker@example.com"


def test_me_returns_the_signed_in_user_and_their_workspaces(
    client: TestClient, email_port: FakeEmailPort
) -> None:
    sign_in(client, email_port, USER)

    body = client.get("/me").json()

    assert body["user"]["email"] == USER
    assert [(w["kind"], w["role"]) for w in body["workspaces"]] == [("personal", "owner")]
    assert body["workspaces"][0]["name"] == f"{USER}'s workspace"


def test_me_lists_team_workspaces_with_the_users_own_role(
    client_factory: Callable[[], TestClient], email_port: FakeEmailPort
) -> None:
    owner = client_factory()
    sign_in(owner, email_port, USER)
    team_id = owner.post("/workspaces", json={"name": "Team Wiki"}).json()["id"]
    owner.post(f"/workspaces/{team_id}/members", json={"email": "ed@example.com", "role": "editor"})

    editor = client_factory()
    sign_in(editor, email_port, "ed@example.com")

    workspaces = editor.get("/me").json()["workspaces"]

    assert {w["id"]: w["role"] for w in workspaces}[team_id] == "editor"


def test_me_rejects_an_unauthenticated_caller(client: TestClient) -> None:
    assert client.get("/me").status_code == 401


def test_workspace_api_lists_agent_subfolders_alongside_the_tree(
    client: TestClient, email_port: FakeEmailPort
) -> None:
    sign_in(client, email_port, USER)
    for path in ("agents/writer/prompt.md", "agents/editor/prompt.md", "notes.md"):
        proposal = client.post(
            "/workspace/files/propose", json={"path": path, "content": "x"}
        ).json()
        client.post(f"/workspace/proposals/{proposal['id']}/approve")

    body = client.get("/workspace/api").json()

    assert body["agents"] == ["editor", "writer"]
    assert body["tree"] == ["agents/editor/prompt.md", "agents/writer/prompt.md", "notes.md"]


def test_workspace_api_reports_no_agents_for_an_empty_workspace(
    client: TestClient, email_port: FakeEmailPort
) -> None:
    sign_in(client, email_port, USER)

    body = client.get("/workspace/api").json()

    assert body["agents"] == []
    assert body["tree"] == []
