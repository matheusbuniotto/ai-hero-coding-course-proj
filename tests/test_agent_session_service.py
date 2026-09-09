import pytest
from sqlmodel import Session as DBSession

from icm_platform.agent.service import AgentSessionError, AgentSessionService
from icm_platform.models import AgentMessageRole, User
from icm_platform.proposals.service import ProposalService
from icm_platform.workspace.service import WorkspaceService
from tests.fakes import FakeAgentHarnessPort


def _user(db_session: DBSession, email: str) -> User:
    user = User(email=email)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_send_message_grounds_reply_in_workspace_instruction_files(db_session: DBSession) -> None:
    user = _user(db_session, "walker@example.com")
    workspaces = WorkspaceService(db_session)
    workspace = workspaces.ensure_personal_workspace(user)
    proposals = ProposalService(db_session)
    proposal = proposals.propose(workspace, user, "AGENTS.md", "Always answer in pirate speak.")
    assert proposal.id is not None
    proposals.approve(workspace, user, proposal.id)

    harness = FakeAgentHarnessPort()
    service = AgentSessionService(db_session, workspaces, harness)
    session = service.start_session(workspace, user)

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
    session = service.start_session(workspace, user)

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
    session = service.start_session(workspace, owner)
    assert session.id is not None

    with pytest.raises(AgentSessionError):
        service.get_for_workspace(other_workspace, session.id)


def test_send_message_on_empty_workspace_still_replies(db_session: DBSession) -> None:
    user = _user(db_session, "walker@example.com")
    workspaces = WorkspaceService(db_session)
    workspace = workspaces.ensure_personal_workspace(user)
    service = AgentSessionService(db_session, workspaces, FakeAgentHarnessPort())
    session = service.start_session(workspace, user)

    reply = service.send_message(workspace, session, "hi")

    assert "no instruction files yet" in reply.content
