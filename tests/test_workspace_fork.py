from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from tests.conftest import sign_in
from tests.fakes import FakeEmailPort

OWNER = "owner@acme.com"
SAME_ORG_VIEWER = "viewer@acme.com"
OTHER_ORG_MEMBER = "member@other-corp.com"
OUTSIDER = "outsider@acme.com"


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
def source_id(owner: TestClient) -> int:
    response = owner.post("/workspaces", json={"name": "Source"})
    assert response.status_code == 200
    workspace_id = response.json()["id"]
    proposal = owner.post(
        f"/workspace/files/propose?workspace_id={workspace_id}",
        json={"path": "a.md", "content": "original"},
    ).json()
    owner.post(f"/workspace/proposals/{proposal['id']}/approve?workspace_id={workspace_id}")
    return workspace_id


def _invite(owner: TestClient, workspace_id: int, email: str, role: str) -> None:
    response = owner.post(
        f"/workspaces/{workspace_id}/members", json={"email": email, "role": role}
    )
    assert response.status_code == 200


def test_viewer_can_fork_a_workspace_they_can_see(
    owner: TestClient, source_id: int, sign_in_as: Callable[[str], TestClient]
) -> None:
    _invite(owner, source_id, SAME_ORG_VIEWER, "viewer")
    viewer = sign_in_as(SAME_ORG_VIEWER)

    response = viewer.post(f"/workspaces/{source_id}/fork", json={"name": "My Fork"})

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "My Fork"
    assert body["role"] == "owner"
    assert viewer.get(f"/workspace/api?workspace_id={body['id']}").json()["tree"] == ["a.md"]


def test_forked_files_are_independent_of_the_source(
    owner: TestClient, source_id: int, sign_in_as: Callable[[str], TestClient]
) -> None:
    _invite(owner, source_id, SAME_ORG_VIEWER, "viewer")
    viewer = sign_in_as(SAME_ORG_VIEWER)
    fork_id = viewer.post(f"/workspaces/{source_id}/fork", json={"name": "My Fork"}).json()["id"]

    source_edit = owner.post(
        f"/workspace/files/propose?workspace_id={source_id}",
        json={"path": "a.md", "content": "changed in source"},
    ).json()
    owner.post(f"/workspace/proposals/{source_edit['id']}/approve?workspace_id={source_id}")

    fork_edit = viewer.post(
        f"/workspace/files/propose?workspace_id={fork_id}",
        json={"path": "b.md", "content": "only in fork"},
    ).json()
    viewer.post(f"/workspace/proposals/{fork_edit['id']}/approve?workspace_id={fork_id}")

    assert owner.get(f"/workspace/api?workspace_id={source_id}").json()["tree"] == ["a.md"]
    assert viewer.get(f"/workspace/api?workspace_id={fork_id}").json()["tree"] == ["a.md", "b.md"]


def test_can_fork_only_a_subfolder_of_the_source(
    owner: TestClient, sign_in_as: Callable[[str], TestClient]
) -> None:
    response = owner.post("/workspaces", json={"name": "Multi-agent Source"})
    workspace_id = response.json()["id"]
    for path, content in [
        ("agent-a/instructions.md", "a-instructions"),
        ("agent-a/notes.md", "a-notes"),
        ("agent-b/instructions.md", "b-instructions"),
    ]:
        proposal = owner.post(
            f"/workspace/files/propose?workspace_id={workspace_id}",
            json={"path": path, "content": content},
        ).json()
        owner.post(f"/workspace/proposals/{proposal['id']}/approve?workspace_id={workspace_id}")
    _invite(owner, workspace_id, SAME_ORG_VIEWER, "viewer")
    viewer = sign_in_as(SAME_ORG_VIEWER)

    response = viewer.post(
        f"/workspaces/{workspace_id}/fork",
        json={"name": "Agent A Fork", "path_prefix": "agent-a"},
    )

    assert response.status_code == 200
    fork_id = response.json()["id"]
    assert viewer.get(f"/workspace/api?workspace_id={fork_id}").json()["tree"] == [
        "agent-a/instructions.md",
        "agent-a/notes.md",
    ]


def test_cannot_fork_a_workspace_from_a_different_org(
    owner: TestClient, source_id: int, sign_in_as: Callable[[str], TestClient]
) -> None:
    _invite(owner, source_id, OTHER_ORG_MEMBER, "viewer")
    other_org_member = sign_in_as(OTHER_ORG_MEMBER)

    response = other_org_member.post(
        f"/workspaces/{source_id}/fork", json={"name": "Cross-org Fork"}
    )

    assert response.status_code == 403
    assert "org" in response.json()["detail"]


def test_cannot_fork_a_workspace_without_at_least_viewer_access(
    source_id: int, sign_in_as: Callable[[str], TestClient]
) -> None:
    outsider = sign_in_as(OUTSIDER)

    response = outsider.post(f"/workspaces/{source_id}/fork", json={"name": "Steal"})

    assert response.status_code == 403
