from collections.abc import Callable

from fastapi.testclient import TestClient

from icm_platform.sandbox.ports import SandboxFile, SandboxResult
from tests.conftest import sign_in as _sign_in
from tests.fakes import FakeEmailPort, FakeSandboxPort


def _start_session(client: TestClient) -> int:
    return client.post("/workspace/agent/sessions", json={"agent_name": "support"}).json()["id"]


def _approve_file(client: TestClient, path: str, content: str) -> None:
    proposal = client.post(
        "/workspace/files/propose", json={"path": path, "content": content}
    ).json()
    client.post(f"/workspace/proposals/{proposal['id']}/approve")


def test_execution_result_and_produced_files_are_visible_in_the_session(
    client: TestClient, email_port: FakeEmailPort, sandbox: FakeSandboxPort
) -> None:
    _sign_in(client, email_port, "walker@example.com")
    _approve_file(client, "agents/support/greet.py", "print('ahoy')")
    session_id = _start_session(client)
    sandbox.results = [
        SandboxResult(
            exit_code=0,
            stdout="ahoy\n",
            stderr="",
            files=[SandboxFile(path="agents/support/out.txt", content="ahoy")],
        )
    ]

    response = client.post(
        f"/workspace/agent/sessions/{session_id}/executions",
        json={"command": "python agents/support/greet.py"},
    )

    assert response.status_code == 200
    execution = response.json()
    assert execution["status"] == "succeeded"
    assert execution["exit_code"] == 0
    assert execution["stdout"] == "ahoy\n"
    assert execution["produced"] == ["agents/support/out.txt"]

    listed = client.get(f"/workspace/agent/sessions/{session_id}/executions").json()
    assert [e["command"] for e in listed] == ["python agents/support/greet.py"]

    files = client.get(f"/workspace/agent/sessions/{session_id}/files").json()
    assert {f["path"] for f in files} == {"agents/support/greet.py", "agents/support/out.txt"}


def test_execution_never_changes_the_canonical_tree(
    client: TestClient, email_port: FakeEmailPort, sandbox: FakeSandboxPort
) -> None:
    _sign_in(client, email_port, "walker@example.com")
    _approve_file(client, "agents/support/greet.py", "print('ahoy')")
    session_id = _start_session(client)
    sandbox.results = [
        SandboxResult(
            exit_code=0,
            stdout="",
            stderr="",
            files=[SandboxFile(path="agents/support/greet.py", content="print('rewritten')")],
        )
    ]

    client.post(f"/workspace/agent/sessions/{session_id}/executions", json={"command": "rewrite"})

    assert client.get("/workspace/api").json()["tree"] == ["agents/support/greet.py"]
    files = {
        f["path"]: f["content"]
        for f in client.get(f"/workspace/agent/sessions/{session_id}/files").json()
    }
    assert files["agents/support/greet.py"] == "print('rewritten')"


def test_a_sandbox_failure_is_reported_without_breaking_the_session(
    client: TestClient, email_port: FakeEmailPort, sandbox: FakeSandboxPort
) -> None:
    _sign_in(client, email_port, "walker@example.com")
    session_id = _start_session(client)
    sandbox.error = "provider unreachable"

    response = client.post(
        f"/workspace/agent/sessions/{session_id}/executions", json={"command": "python greet.py"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "errored"
    assert "provider unreachable" in response.json()["stderr"]

    chat = client.post(
        f"/workspace/agent/sessions/{session_id}/messages", json={"message": "what happened?"}
    )
    assert chat.status_code == 200


def test_viewers_may_not_run_code(
    client_factory: Callable[[], TestClient], email_port: FakeEmailPort
) -> None:
    owner = client_factory()
    _sign_in(owner, email_port, "owner@example.com")
    team_id = owner.post("/workspaces", json={"name": "Team"}).json()["id"]
    owner.post(
        f"/workspaces/{team_id}/members",
        json={"email": "viewer@example.com", "role": "viewer"},
    )
    session_id = owner.post(
        f"/workspace/agent/sessions?workspace_id={team_id}", json={"agent_name": "support"}
    ).json()["id"]

    viewer = client_factory()
    _sign_in(viewer, email_port, "viewer@example.com")
    denied = viewer.post(
        f"/workspace/agent/sessions/{session_id}/executions?workspace_id={team_id}",
        json={"command": "rm -rf /"},
    )

    assert denied.status_code == 403


def test_execution_endpoints_require_auth(client: TestClient) -> None:
    assert (
        client.post("/workspace/agent/sessions/1/executions", json={"command": "ls"}).status_code
        == 401
    )
    assert client.get("/workspace/agent/sessions/1/executions").status_code == 401
    assert client.get("/workspace/agent/sessions/1/files").status_code == 401
