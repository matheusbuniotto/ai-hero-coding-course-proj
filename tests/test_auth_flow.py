from fastapi.testclient import TestClient
from sqlmodel import Session as DBSession
from sqlmodel import select

from icm_platform.models import Workspace
from tests.fakes import FakeEmailPort


def _request_and_extract_token(client: TestClient, email_port: FakeEmailPort, email: str) -> str:
    response = client.post("/auth/magic-link", data={"email": email})
    assert response.status_code == 200
    link = email_port.sent[-1][1]
    return link.split("token=")[1]


def test_full_magic_link_sign_in_creates_workspace(
    client: TestClient, email_port: FakeEmailPort
) -> None:
    token = _request_and_extract_token(client, email_port, "walker@example.com")

    verify_response = client.get(f"/auth/verify?token={token}", follow_redirects=False)
    assert verify_response.status_code == 303
    assert verify_response.headers["location"] == "/"
    assert "session_token" in verify_response.cookies

    workspace_response = client.get("/workspace/api")
    assert workspace_response.status_code == 200
    body = workspace_response.json()
    assert body["name"] == "walker@example.com's workspace"
    assert body["tree"] == []


def test_workspace_is_created_on_sign_in_not_lazily_on_view(
    client: TestClient, email_port: FakeEmailPort, db_session: DBSession
) -> None:
    token = _request_and_extract_token(client, email_port, "walker@example.com")

    client.get(f"/auth/verify?token={token}", follow_redirects=False)

    workspace = db_session.exec(select(Workspace)).first()
    assert workspace is not None
    assert workspace.name == "walker@example.com's workspace"


def test_workspace_html_view_shows_empty_tree(
    client: TestClient, email_port: FakeEmailPort
) -> None:
    token = _request_and_extract_token(client, email_port, "walker@example.com")
    client.get(f"/auth/verify?token={token}")

    response = client.get("/workspace")

    assert response.status_code == 200
    assert "Empty workspace" in response.text


def test_unauthenticated_workspace_access_is_rejected(client: TestClient) -> None:
    response = client.get("/workspace/api")
    assert response.status_code == 401


def test_invalid_magic_link_token_redirects_to_login(client: TestClient) -> None:
    response = client.get("/auth/verify?token=bogus", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/auth/login")


def test_session_persists_across_requests_until_logout(
    client: TestClient, email_port: FakeEmailPort
) -> None:
    token = _request_and_extract_token(client, email_port, "walker@example.com")
    client.get(f"/auth/verify?token={token}")

    assert client.get("/workspace/api").status_code == 200
    assert client.get("/workspace/api").status_code == 200

    client.post("/auth/logout")

    assert client.get("/workspace/api").status_code == 401
