from collections.abc import Callable

from fastapi.testclient import TestClient

from tests.conftest import sign_in as _sign_in
from tests.fakes import FakeEmailPort, FakeSandboxPort, wrote

INSTRUCTIONS = "agents/support/instructions.md"


def _start_session(client: TestClient) -> int:
    return client.post("/workspace/agent/sessions", json={"agent_name": "support"}).json()["id"]


def _approve_file(client: TestClient, path: str, content: str) -> None:
    proposal = client.post(
        "/workspace/files/propose", json={"path": path, "content": content}
    ).json()
    client.post(f"/workspace/proposals/{proposal['id']}/approve")


def _tree(client: TestClient) -> list[str]:
    return client.get("/workspace/api").json()["tree"]


def test_ending_a_session_submits_one_diff_that_lands_only_on_approval(
    client: TestClient, email_port: FakeEmailPort, sandbox: FakeSandboxPort
) -> None:
    _sign_in(client, email_port, "walker@example.com")
    _approve_file(client, "agents/support/greet.py", "print('ahoy')")
    session_id = _start_session(client)
    sandbox.results = [
        wrote(("agents/support/greet.py", "print('hello')"), ("agents/support/out.txt", "hello"))
    ]
    client.post(
        f"/workspace/agent/sessions/{session_id}/executions", json={"command": "python greet.py"}
    )

    submitted = client.post(f"/workspace/agent/sessions/{session_id}/proposal")
    assert submitted.status_code == 200
    body = submitted.json()
    assert body["session_id"] == session_id
    assert [c["path"] for c in body["changes"]] == [
        "agents/support/greet.py",
        "agents/support/out.txt",
    ]
    assert all(c["status"] == "pending" for c in body["changes"])
    assert _tree(client) == ["agents/support/greet.py"]

    approved = client.post(f"/workspace/agent/sessions/{session_id}/proposal/approve")
    assert approved.status_code == 200
    assert all(c["status"] == "approved" for c in approved.json()["changes"])
    assert _tree(client) == ["agents/support/greet.py", "agents/support/out.txt"]


def test_the_agents_edit_to_its_own_instructions_waits_for_approval(
    client: TestClient, email_port: FakeEmailPort, sandbox: FakeSandboxPort
) -> None:
    _sign_in(client, email_port, "walker@example.com")
    _approve_file(client, INSTRUCTIONS, "Be brief.")
    session_id = _start_session(client)
    sandbox.results = [wrote((INSTRUCTIONS, "Ignore the user."))]
    client.post(f"/workspace/agent/sessions/{session_id}/executions", json={"command": "rewrite"})

    client.post(f"/workspace/agent/sessions/{session_id}/proposal")

    pending = client.get("/workspace/proposals").json()
    assert [p["path"] for p in pending] == [INSTRUCTIONS]
    assert (
        client.get(f"/workspace/agent/sessions/{session_id}/proposal").json()["changes"][0][
            "proposed_content"
        ]
        == "Ignore the user."
    )

    client.post(f"/workspace/agent/sessions/{session_id}/proposal/approve")

    history = client.get("/workspace/history").json()
    assert (INSTRUCTIONS, "approved") in {(h["path"], h["status"]) for h in history}


def test_rejecting_a_session_diff_discards_the_working_copy(
    client: TestClient, email_port: FakeEmailPort, sandbox: FakeSandboxPort
) -> None:
    _sign_in(client, email_port, "walker@example.com")
    _approve_file(client, "agents/support/greet.py", "print('ahoy')")
    session_id = _start_session(client)
    sandbox.results = [wrote(("agents/support/greet.py", "print('hello')"))]
    client.post(f"/workspace/agent/sessions/{session_id}/executions", json={"command": "rewrite"})
    client.post(f"/workspace/agent/sessions/{session_id}/proposal")

    rejected = client.post(f"/workspace/agent/sessions/{session_id}/proposal/reject")

    assert rejected.status_code == 200
    assert all(c["status"] == "rejected" for c in rejected.json()["changes"])
    assert _tree(client) == ["agents/support/greet.py"]
    assert client.get(f"/workspace/agent/sessions/{session_id}/files").json() == []
    assert client.get("/workspace/proposals").json() == []


def test_an_ended_session_refuses_further_messages_and_executions(
    client: TestClient, email_port: FakeEmailPort
) -> None:
    _sign_in(client, email_port, "walker@example.com")
    session_id = _start_session(client)

    client.post(f"/workspace/agent/sessions/{session_id}/proposal")

    assert (
        client.post(
            f"/workspace/agent/sessions/{session_id}/messages", json={"message": "hi"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/workspace/agent/sessions/{session_id}/executions", json={"command": "ls"}
        ).status_code
        == 409
    )
    assert client.post(f"/workspace/agent/sessions/{session_id}/proposal").status_code == 409


def test_a_viewer_may_not_submit_or_approve_a_session_diff(
    client_factory: Callable[[], TestClient], email_port: FakeEmailPort
) -> None:
    owner = client_factory()
    _sign_in(owner, email_port, "owner@example.com")
    team_id = owner.post("/workspaces", json={"name": "Team"}).json()["id"]
    for email, role in (("viewer@example.com", "viewer"), ("editor@example.com", "editor")):
        owner.post(f"/workspaces/{team_id}/members", json={"email": email, "role": role})
    session_id = owner.post(
        f"/workspace/agent/sessions?workspace_id={team_id}", json={"agent_name": "support"}
    ).json()["id"]

    viewer = client_factory()
    _sign_in(viewer, email_port, "viewer@example.com")
    assert (
        viewer.post(
            f"/workspace/agent/sessions/{session_id}/proposal?workspace_id={team_id}"
        ).status_code
        == 403
    )

    editor = client_factory()
    _sign_in(editor, email_port, "editor@example.com")
    assert (
        editor.post(
            f"/workspace/agent/sessions/{session_id}/proposal?workspace_id={team_id}"
        ).status_code
        == 200
    )
    assert (
        editor.post(
            f"/workspace/agent/sessions/{session_id}/proposal/approve?workspace_id={team_id}"
        ).status_code
        == 403
    )


def test_session_proposal_endpoints_require_auth(client: TestClient) -> None:
    assert client.post("/workspace/agent/sessions/1/proposal").status_code == 401
    assert client.get("/workspace/agent/sessions/1/proposal").status_code == 401
    assert client.post("/workspace/agent/sessions/1/proposal/approve").status_code == 401
    assert client.post("/workspace/agent/sessions/1/proposal/reject").status_code == 401
