from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from tests.conftest import sign_in
from tests.fakes import FakeEmailPort

OWNER = "owner@example.com"
EDITOR = "editor@example.com"
VIEWER = "viewer@example.com"
OUTSIDER = "outsider@example.com"


@pytest.fixture
def sign_in_as(
    client_factory: Callable[[], TestClient], email_port: FakeEmailPort
) -> Callable[[str], TestClient]:
    def _sign_in_as(email: str) -> TestClient:
        client = client_factory()
        sign_in(client, email_port, email)
        return client

    return _sign_in_as


@pytest.fixture
def owner(sign_in_as: Callable[[str], TestClient]) -> TestClient:
    return sign_in_as(OWNER)


@pytest.fixture
def team_id(owner: TestClient) -> int:
    response = owner.post("/workspaces", json={"name": "Team Wiki"})
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "team"
    assert body["role"] == "owner"
    return body["id"]


def _invite(owner: TestClient, team_id: int, email: str, role: str) -> None:
    response = owner.post(f"/workspaces/{team_id}/members", json={"email": email, "role": role})
    assert response.status_code == 200


def test_editor_can_propose_but_not_approve(
    owner: TestClient, team_id: int, sign_in_as: Callable[[str], TestClient]
) -> None:
    _invite(owner, team_id, EDITOR, "editor")
    editor = sign_in_as(EDITOR)

    proposal = editor.post(
        f"/workspace/files/propose?workspace_id={team_id}", json={"path": "a.md", "content": "hi"}
    )
    assert proposal.status_code == 200

    denied = editor.post(
        f"/workspace/proposals/{proposal.json()['id']}/approve?workspace_id={team_id}"
    )
    assert denied.status_code == 403
    assert "editor" in denied.json()["detail"]


def test_owner_approves_an_editors_proposal(
    owner: TestClient, team_id: int, sign_in_as: Callable[[str], TestClient]
) -> None:
    _invite(owner, team_id, EDITOR, "editor")
    editor = sign_in_as(EDITOR)
    proposal = editor.post(
        f"/workspace/files/propose?workspace_id={team_id}", json={"path": "a.md", "content": "hi"}
    ).json()

    approved = owner.post(f"/workspace/proposals/{proposal['id']}/approve?workspace_id={team_id}")

    assert approved.status_code == 200
    assert owner.get(f"/workspace/api?workspace_id={team_id}").json()["tree"] == ["a.md"]


def test_viewer_can_read_but_not_propose_or_approve(
    owner: TestClient, team_id: int, sign_in_as: Callable[[str], TestClient]
) -> None:
    _invite(owner, team_id, EDITOR, "editor")
    _invite(owner, team_id, VIEWER, "viewer")
    editor = sign_in_as(EDITOR)
    viewer = sign_in_as(VIEWER)
    proposal = editor.post(
        f"/workspace/files/propose?workspace_id={team_id}", json={"path": "a.md", "content": "hi"}
    ).json()

    assert viewer.get(f"/workspace/api?workspace_id={team_id}").status_code == 200
    assert viewer.get(f"/workspace/proposals?workspace_id={team_id}").status_code == 200

    proposed = viewer.post(
        f"/workspace/files/propose?workspace_id={team_id}", json={"path": "b.md", "content": "no"}
    )
    approved = viewer.post(f"/workspace/proposals/{proposal['id']}/approve?workspace_id={team_id}")
    rejected = viewer.post(f"/workspace/proposals/{proposal['id']}/reject?workspace_id={team_id}")

    assert [proposed.status_code, approved.status_code, rejected.status_code] == [403, 403, 403]
    assert "viewer" in proposed.json()["detail"]


def test_only_owners_manage_membership(
    owner: TestClient, team_id: int, sign_in_as: Callable[[str], TestClient]
) -> None:
    _invite(owner, team_id, EDITOR, "editor")
    editor = sign_in_as(EDITOR)

    denied = editor.post(f"/workspaces/{team_id}/members", json={"email": VIEWER, "role": "viewer"})
    assert denied.status_code == 403

    assert owner.get(f"/workspaces/{team_id}/members").status_code == 200
    assert editor.get(f"/workspaces/{team_id}/members").status_code == 200


def test_removed_member_loses_access(
    owner: TestClient, team_id: int, sign_in_as: Callable[[str], TestClient]
) -> None:
    _invite(owner, team_id, EDITOR, "editor")
    editor = sign_in_as(EDITOR)
    member = next(
        m for m in owner.get(f"/workspaces/{team_id}/members").json() if m["email"] == EDITOR
    )

    removed = owner.delete(f"/workspaces/{team_id}/members/{member['user_id']}")

    assert removed.status_code == 200
    assert editor.get(f"/workspace/api?workspace_id={team_id}").status_code == 403


def test_non_member_cannot_touch_the_workspace(
    team_id: int, sign_in_as: Callable[[str], TestClient]
) -> None:
    outsider = sign_in_as(OUTSIDER)

    assert outsider.get(f"/workspace/api?workspace_id={team_id}").status_code == 403
    assert (
        outsider.post(
            f"/workspace/files/propose?workspace_id={team_id}",
            json={"path": "a.md", "content": "x"},
        ).status_code
        == 403
    )
    assert outsider.get(f"/workspace/files?path=a.md&workspace_id={team_id}").status_code == 403


def test_viewer_can_read_a_file(
    owner: TestClient, team_id: int, sign_in_as: Callable[[str], TestClient]
) -> None:
    _invite(owner, team_id, VIEWER, "viewer")
    proposal = owner.post(
        f"/workspace/files/propose?workspace_id={team_id}", json={"path": "a.md", "content": "hi"}
    ).json()
    owner.post(f"/workspace/proposals/{proposal['id']}/approve?workspace_id={team_id}")
    viewer = sign_in_as(VIEWER)

    response = viewer.get(f"/workspace/files?path=a.md&workspace_id={team_id}")

    assert response.status_code == 200
    assert response.json() == {"path": "a.md", "content": "hi"}


def test_team_workspace_is_separate_from_the_personal_one(owner: TestClient, team_id: int) -> None:
    proposal = owner.post(
        f"/workspace/files/propose?workspace_id={team_id}",
        json={"path": "team.md", "content": "shared"},
    ).json()
    owner.post(f"/workspace/proposals/{proposal['id']}/approve?workspace_id={team_id}")

    assert owner.get("/workspace/api").json()["tree"] == []

    listed = owner.get("/workspaces").json()
    assert [(w["kind"], w["role"]) for w in listed] == [("personal", "owner"), ("team", "owner")]


def test_workspace_endpoints_require_auth(client: TestClient) -> None:
    assert client.post("/workspaces", json={"name": "Team Wiki"}).status_code == 401
    assert client.get("/workspaces").status_code == 401
