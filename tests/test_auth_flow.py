import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session as DBSession
from sqlmodel import select

from icm_platform.models import User, Workspace
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


@pytest.fixture
def dev_auth_enabled() -> Iterator[None]:
    os.environ["ICM_DEV_AUTH"] = "1"
    try:
        yield
    finally:
        del os.environ["ICM_DEV_AUTH"]


def test_dev_login_is_a_404_when_the_flag_is_off(client: TestClient) -> None:
    response = client.post("/auth/dev-login", data={"email": "walker@example.com"})
    assert response.status_code == 404


def test_login_page_has_no_dev_form_when_the_flag_is_off(client: TestClient) -> None:
    response = client.get("/auth/login")
    assert "dev-login" not in response.text


def test_dev_login_signs_in_without_a_magic_link(
    client: TestClient, dev_auth_enabled: None
) -> None:
    response = client.post(
        "/auth/dev-login", data={"email": "walker@example.com"}, follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert "session_token" in response.cookies

    workspace_response = client.get("/workspace/api")
    assert workspace_response.status_code == 200
    assert workspace_response.json()["name"] == "walker@example.com's workspace"


def test_dev_login_reuses_the_existing_user_on_a_second_sign_in(
    client: TestClient, dev_auth_enabled: None, db_session: DBSession
) -> None:
    client.post("/auth/dev-login", data={"email": "walker@example.com"})
    client.post("/auth/logout")
    client.post("/auth/dev-login", data={"email": "walker@example.com"})

    users = db_session.exec(select(User).where(User.email == "walker@example.com")).all()
    assert len(users) == 1


def test_login_page_offers_dev_sign_in_when_the_flag_is_on(
    client: TestClient, dev_auth_enabled: None
) -> None:
    response = client.get("/auth/login")
    assert "dev-login" in response.text
