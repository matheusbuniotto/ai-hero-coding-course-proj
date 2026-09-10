from collections.abc import Callable

from fastapi.testclient import TestClient

from tests.conftest import sign_in as _sign_in
from tests.fakes import FakeAgentHarnessPort, FakeEmailPort


def test_chat_session_grounds_replies_in_approved_instruction_files(
    client: TestClient, email_port: FakeEmailPort, agent_harness: FakeAgentHarnessPort
) -> None:
    _sign_in(client, email_port, "walker@example.com")
    proposal = client.post(
        "/workspace/files/propose",
        json={"path": "agents/support/AGENTS.md", "content": "Always answer in pirate speak."},
    ).json()
    client.post(f"/workspace/proposals/{proposal['id']}/approve")

    session = client.post("/workspace/agent/sessions", json={"agent_name": "support"}).json()
    assert session["id"] is not None
    assert session["agent_name"] == "support"

    response = client.post(
        f"/workspace/agent/sessions/{session['id']}/messages", json={"message": "hello"}
    )
    assert response.status_code == 200
    reply = response.json()
    assert reply["role"] == "assistant"
    assert "Always answer in pirate speak." in reply["content"]

    messages = client.get(f"/workspace/agent/sessions/{session['id']}/messages").json()
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "hello"
    assert messages[1]["content"] == reply["content"]


def test_second_message_carries_prior_turns_as_history(
    client: TestClient, email_port: FakeEmailPort, agent_harness: FakeAgentHarnessPort
) -> None:
    _sign_in(client, email_port, "walker@example.com")
    session = client.post("/workspace/agent/sessions", json={"agent_name": "support"}).json()

    client.post(f"/workspace/agent/sessions/{session['id']}/messages", json={"message": "first"})
    client.post(f"/workspace/agent/sessions/{session['id']}/messages", json={"message": "second"})

    _, second_history, second_message = agent_harness.calls[1]
    assert second_message == "second"
    assert len(second_history) == 2


def test_agent_session_endpoints_require_auth(client: TestClient) -> None:
    assert (
        client.post("/workspace/agent/sessions", json={"agent_name": "support"}).status_code == 401
    )
    assert (
        client.post("/workspace/agent/sessions/1/messages", json={"message": "hi"}).status_code
        == 401
    )
    assert client.get("/workspace/agent/sessions/1/messages").status_code == 401


def test_cannot_message_a_session_from_another_workspace(
    client_factory: Callable[[], TestClient], email_port: FakeEmailPort
) -> None:
    owner_client = client_factory()
    _sign_in(owner_client, email_port, "owner@example.com")
    session = owner_client.post("/workspace/agent/sessions", json={"agent_name": "support"}).json()

    other_client = client_factory()
    _sign_in(other_client, email_port, "other@example.com")
    response = other_client.post(
        f"/workspace/agent/sessions/{session['id']}/messages", json={"message": "hi"}
    )
    assert response.status_code == 404


def test_lists_agent_subfolders_and_scopes_context_to_the_selected_one(
    client: TestClient, email_port: FakeEmailPort, agent_harness: FakeAgentHarnessPort
) -> None:
    _sign_in(client, email_port, "walker@example.com")
    for path, content in [
        ("agents/support/AGENTS.md", "Support agent: pirate speak only."),
        ("agents/docs/AGENTS.md", "Docs agent: formal English only."),
    ]:
        proposal = client.post(
            "/workspace/files/propose", json={"path": path, "content": content}
        ).json()
        client.post(f"/workspace/proposals/{proposal['id']}/approve")

    agents = client.get("/workspace/agent/agents").json()
    assert agents == ["docs", "support"]

    session = client.post("/workspace/agent/sessions", json={"agent_name": "docs"}).json()
    response = client.post(
        f"/workspace/agent/sessions/{session['id']}/messages", json={"message": "hi"}
    )
    reply = response.json()
    assert "formal English only" in reply["content"]
    assert "pirate speak" not in reply["content"]
