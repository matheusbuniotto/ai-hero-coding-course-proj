import pytest
from sqlmodel import Session as DBSession

from icm_platform.agent.execution import CodeExecutionService
from icm_platform.agent.lifecycle import AgentSessionError
from icm_platform.agent.service import AgentSessionService
from icm_platform.models import AgentMessageRole, User, WorkspaceRole
from icm_platform.proposals.service import ProposalService
from icm_platform.sandbox.ports import SandboxResult
from icm_platform.workspace.service import WorkspaceService
from tests.fakes import FakeAgentHarnessPort, FakeSandboxPort


def _user(db_session: DBSession, email: str) -> User:
    user = User(email=email)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_send_message_grounds_reply_in_agent_instruction_files(db_session: DBSession) -> None:
    user = _user(db_session, "walker@example.com")
    workspaces = WorkspaceService(db_session)
    workspace = workspaces.ensure_personal_workspace(user)
    proposals = ProposalService(db_session)
    proposal = proposals.propose(
        workspace, user, "agents/support/AGENTS.md", "Always answer in pirate speak."
    )
    assert proposal.id is not None
    proposals.approve(workspace, user, proposal.id)

    harness = FakeAgentHarnessPort()
    service = AgentSessionService(db_session, workspaces, harness)
    session = service.start_session(workspace, user, "support")

    reply = service.send_message(workspace, session, "How should I greet a user?")

    assert reply.role == AgentMessageRole.assistant
    assert "Always answer in pirate speak." in reply.content
    instructions, history, message = harness.calls[0]
    assert "Always answer in pirate speak." in instructions
    assert history == []
    assert message == "How should I greet a user?"


def test_send_message_passes_prior_turns_as_history(db_session: DBSession) -> None:
    user = _user(db_session, "walker@example.com")
    workspaces = WorkspaceService(db_session)
    workspace = workspaces.ensure_personal_workspace(user)
    harness = FakeAgentHarnessPort()
    service = AgentSessionService(db_session, workspaces, harness)
    session = service.start_session(workspace, user, "support")

    first_reply = service.send_message(workspace, session, "first")
    service.send_message(workspace, session, "second")

    _, second_history, second_message = harness.calls[1]
    assert second_message == "second"
    assert [turn.role for turn in second_history] == ["user", "assistant"]
    assert [turn.content for turn in second_history] == ["first", first_reply.content]


def test_get_for_workspace_rejects_session_from_another_workspace(db_session: DBSession) -> None:
    owner = _user(db_session, "owner@example.com")
    other = _user(db_session, "other@example.com")
    workspaces = WorkspaceService(db_session)
    workspace = workspaces.ensure_personal_workspace(owner)
    other_workspace = workspaces.ensure_personal_workspace(other)
    service = AgentSessionService(db_session, workspaces, FakeAgentHarnessPort())
    session = service.start_session(workspace, owner, "support")
    assert session.id is not None

    with pytest.raises(AgentSessionError):
        service.get_for_workspace(other_workspace, session.id)


def test_send_message_on_empty_agent_folder_still_replies(db_session: DBSession) -> None:
    user = _user(db_session, "walker@example.com")
    workspaces = WorkspaceService(db_session)
    workspace = workspaces.ensure_personal_workspace(user)
    service = AgentSessionService(db_session, workspaces, FakeAgentHarnessPort())
    session = service.start_session(workspace, user, "support")

    reply = service.send_message(workspace, session, "hi")

    assert "no instruction files yet" in reply.content


def test_context_is_isolated_between_agent_subfolders(db_session: DBSession) -> None:
    user = _user(db_session, "walker@example.com")
    workspaces = WorkspaceService(db_session)
    workspace = workspaces.ensure_personal_workspace(user)
    proposals = ProposalService(db_session)
    for path, content in [
        ("agents/support/AGENTS.md", "Support agent: always answer in pirate speak."),
        ("agents/docs/AGENTS.md", "Docs agent: always answer in formal English."),
    ]:
        proposal = proposals.propose(workspace, user, path, content)
        assert proposal.id is not None
        proposals.approve(workspace, user, proposal.id)

    harness = FakeAgentHarnessPort()
    service = AgentSessionService(db_session, workspaces, harness)

    support_session = service.start_session(workspace, user, "support")
    service.send_message(workspace, support_session, "hi")
    support_instructions, _, _ = harness.calls[0]
    assert "pirate speak" in support_instructions
    assert "formal English" not in support_instructions

    docs_session = service.start_session(workspace, user, "docs")
    service.send_message(workspace, docs_session, "hi")
    docs_instructions, _, _ = harness.calls[1]
    assert "formal English" in docs_instructions
    assert "pirate speak" not in docs_instructions


def test_agent_name_with_like_wildcards_cannot_leak_other_agents_context(
    db_session: DBSession,
) -> None:
    user = _user(db_session, "walker@example.com")
    workspaces = WorkspaceService(db_session)
    workspace = workspaces.ensure_personal_workspace(user)
    proposals = ProposalService(db_session)
    for path, content in [
        ("agents/support/AGENTS.md", "Support agent: pirate speak only."),
        ("agents/docs/AGENTS.md", "Docs agent: formal English only."),
    ]:
        proposal = proposals.propose(workspace, user, path, content)
        assert proposal.id is not None
        proposals.approve(workspace, user, proposal.id)

    harness = FakeAgentHarnessPort()
    service = AgentSessionService(db_session, workspaces, harness)
    session = service.start_session(workspace, user, "%")

    reply = service.send_message(workspace, session, "hi")

    assert "no instruction files yet" in reply.content


def test_agent_can_request_code_execution_and_sees_the_result(db_session: DBSession) -> None:
    user = _user(db_session, "walker@example.com")
    workspaces = WorkspaceService(db_session)
    workspace = workspaces.ensure_personal_workspace(user)
    sandbox = FakeSandboxPort(
        [SandboxResult(exit_code=0, stdout="ahoy\n", stderr="", files=[])],
    )
    executions = CodeExecutionService(db_session, workspaces, sandbox)
    harness = FakeAgentHarnessPort(run_commands=["python greet.py"])
    service = AgentSessionService(db_session, workspaces, harness, executions)
    session = service.start_session(workspace, user, "support")

    reply = service.send_message(workspace, session, "run the greeter")

    assert "$ python greet.py" in reply.content
    assert "ahoy" in reply.content
    assert [e.command for e in executions.list_executions(session)] == ["python greet.py"]


def test_a_failed_run_reaches_the_conversation_instead_of_raising(db_session: DBSession) -> None:
    user = _user(db_session, "walker@example.com")
    workspaces = WorkspaceService(db_session)
    workspace = workspaces.ensure_personal_workspace(user)
    sandbox = FakeSandboxPort(error="provider unreachable")
    executions = CodeExecutionService(db_session, workspaces, sandbox)
    harness = FakeAgentHarnessPort(run_commands=["python greet.py"])
    service = AgentSessionService(db_session, workspaces, harness, executions)
    session = service.start_session(workspace, user, "support")

    reply = service.send_message(workspace, session, "run the greeter")

    assert "sandbox unavailable: provider unreachable" in reply.content


def test_a_viewer_agent_session_cannot_run_code(db_session: DBSession) -> None:
    owner = _user(db_session, "owner@example.com")
    viewer = _user(db_session, "viewer@example.com")
    workspaces = WorkspaceService(db_session)
    workspace = workspaces.create_team_workspace(owner, "Team")
    workspaces.invite_member(workspace, viewer.email, WorkspaceRole.viewer)
    sandbox = FakeSandboxPort()
    executions = CodeExecutionService(db_session, workspaces, sandbox)
    harness = FakeAgentHarnessPort(run_commands=["python greet.py"])
    service = AgentSessionService(db_session, workspaces, harness, executions)
    session = service.start_session(workspace, viewer, "support")

    reply = service.send_message(workspace, session, "run the greeter")

    assert "refused" in reply.content
    assert sandbox.calls == []


def test_a_session_without_a_sandbox_stays_read_only(db_session: DBSession) -> None:
    user = _user(db_session, "walker@example.com")
    workspaces = WorkspaceService(db_session)
    workspace = workspaces.ensure_personal_workspace(user)
    harness = FakeAgentHarnessPort(run_commands=["python greet.py"])
    service = AgentSessionService(db_session, workspaces, harness)
    session = service.start_session(workspace, user, "support")

    reply = service.send_message(workspace, session, "run the greeter")

    assert "$ python greet.py" not in reply.content
    instructions, _, _ = harness.calls[0]
    assert "You cannot write files or run code." in instructions


def test_list_agents_returns_sorted_subfolder_names(db_session: DBSession) -> None:
    user = _user(db_session, "walker@example.com")
    workspaces = WorkspaceService(db_session)
    workspace = workspaces.ensure_personal_workspace(user)
    proposals = ProposalService(db_session)
    for path in ["agents/support/AGENTS.md", "agents/docs/AGENTS.md"]:
        proposal = proposals.propose(workspace, user, path, "content")
        assert proposal.id is not None
        proposals.approve(workspace, user, proposal.id)

    assert workspaces.list_agents(workspace) == ["docs", "support"]
