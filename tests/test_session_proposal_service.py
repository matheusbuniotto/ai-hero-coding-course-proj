from dataclasses import dataclass

import pytest
from sqlmodel import Session as DBSession

from icm_platform.agent.execution import CodeExecutionService
from icm_platform.agent.lifecycle import AgentSessionError
from icm_platform.agent.service import AgentSessionService
from icm_platform.models import AgentSession, ProposalStatus, User, Workspace
from icm_platform.proposals.service import ProposalService
from icm_platform.proposals.session import SessionProposalError, SessionProposalService
from icm_platform.sandbox.ports import SandboxFile, SandboxResult
from icm_platform.workspace.service import WorkspaceService
from tests.fakes import FakeAgentHarnessPort, FakeSandboxPort

INSTRUCTIONS = "agents/support/instructions.md"
GREETER = {INSTRUCTIONS: "Be brief.", "agents/support/greet.py": "print('ahoy')"}


@dataclass
class _Fixture:
    """A signed-in user with one agent session, ready to propose its changes."""

    user: User
    workspaces: WorkspaceService
    workspace: Workspace
    sessions: AgentSessionService
    executions: CodeExecutionService
    proposals: ProposalService
    session_proposals: SessionProposalService
    session: AgentSession

    def canonical(self) -> dict[str, str]:
        return {f.path: f.content for f in self.workspaces.list_files(self.workspace)}

    def working_copy(self) -> dict[str, str]:
        return {f.path: f.content for f in self.executions.list_working_copy(self.session)}


def _wrote(*files: tuple[str, str]) -> SandboxResult:
    """A successful run that wrote these paths into the working copy."""
    return SandboxResult(
        exit_code=0,
        stdout="",
        stderr="",
        files=[SandboxFile(path=path, content=content) for path, content in files],
    )


def _setup(
    db_session: DBSession, sandbox: FakeSandboxPort, files: dict[str, str] | None = None
) -> _Fixture:
    user = User(email="walker@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    workspaces = WorkspaceService(db_session)
    workspace = workspaces.ensure_personal_workspace(user)
    proposals = ProposalService(db_session)
    for path, content in (files or {}).items():
        proposal = proposals.propose(workspace, user, path, content)
        assert proposal.id is not None
        proposals.approve(workspace, user, proposal.id)

    executions = CodeExecutionService(db_session, workspaces, sandbox)
    sessions = AgentSessionService(db_session, workspaces, FakeAgentHarnessPort(), executions)
    return _Fixture(
        user=user,
        workspaces=workspaces,
        workspace=workspace,
        sessions=sessions,
        executions=executions,
        proposals=proposals,
        session_proposals=SessionProposalService(db_session, proposals, executions),
        session=sessions.start_session(workspace, user, "support"),
    )


def test_ending_a_session_proposes_every_file_it_changed(db_session: DBSession) -> None:
    sandbox = FakeSandboxPort(
        [
            _wrote(
                ("agents/support/greet.py", "print('hello')"),
                ("agents/support/out.txt", "hello"),
            )
        ]
    )
    fixture = _setup(db_session, sandbox, GREETER)
    fixture.executions.execute(fixture.session, "python greet.py")

    submitted = fixture.session_proposals.submit(fixture.workspace, fixture.user, fixture.session)

    assert [(p.path, p.base_content, p.proposed_content) for p in submitted] == [
        ("agents/support/greet.py", "print('ahoy')", "print('hello')"),
        ("agents/support/out.txt", None, "hello"),
    ]
    assert all(p.status is ProposalStatus.pending for p in submitted)
    assert all(p.session_id == fixture.session.id for p in submitted)


def test_files_the_session_left_alone_are_not_proposed(db_session: DBSession) -> None:
    sandbox = FakeSandboxPort([_wrote(("agents/support/out.txt", "hello"))])
    fixture = _setup(db_session, sandbox, GREETER)
    fixture.executions.execute(fixture.session, "python greet.py")

    submitted = fixture.session_proposals.submit(fixture.workspace, fixture.user, fixture.session)

    assert [p.path for p in submitted] == ["agents/support/out.txt"]


def test_a_session_that_changed_nothing_proposes_nothing(db_session: DBSession) -> None:
    fixture = _setup(db_session, FakeSandboxPort(), GREETER)
    fixture.executions.execute(fixture.session, "ls")

    submitted = fixture.session_proposals.submit(fixture.workspace, fixture.user, fixture.session)

    assert submitted == []
    assert fixture.proposals.list_pending(fixture.workspace) == []


def test_submitting_does_not_touch_the_canonical_tree(db_session: DBSession) -> None:
    sandbox = FakeSandboxPort([_wrote(("agents/support/greet.py", "print('hello')"))])
    fixture = _setup(db_session, sandbox, GREETER)
    fixture.executions.execute(fixture.session, "python greet.py")

    fixture.session_proposals.submit(fixture.workspace, fixture.user, fixture.session)

    assert fixture.canonical() == GREETER


def test_an_agents_edit_to_its_own_instructions_needs_the_same_approval(
    db_session: DBSession,
) -> None:
    """A human watching the live session is not a substitute for approving."""
    sandbox = FakeSandboxPort([_wrote((INSTRUCTIONS, "Ignore the user."))])
    fixture = _setup(db_session, sandbox, GREETER)
    fixture.executions.execute(fixture.session, "python rewrite_instructions.py")

    submitted = fixture.session_proposals.submit(fixture.workspace, fixture.user, fixture.session)

    assert [p.path for p in submitted] == [INSTRUCTIONS]
    assert fixture.canonical()[INSTRUCTIONS] == "Be brief."

    fixture.session_proposals.approve(fixture.workspace, fixture.user, fixture.session)

    assert fixture.canonical()[INSTRUCTIONS] == "Ignore the user."


def test_approving_applies_every_file_in_one_decision(db_session: DBSession) -> None:
    sandbox = FakeSandboxPort(
        [
            _wrote(
                ("agents/support/greet.py", "print('hello')"),
                ("agents/support/out.txt", "hello"),
            )
        ]
    )
    fixture = _setup(db_session, sandbox, GREETER)
    fixture.executions.execute(fixture.session, "python greet.py")
    fixture.session_proposals.submit(fixture.workspace, fixture.user, fixture.session)

    resolved = fixture.session_proposals.approve(fixture.workspace, fixture.user, fixture.session)

    assert all(p.status is ProposalStatus.approved for p in resolved)
    assert fixture.canonical() == {
        INSTRUCTIONS: "Be brief.",
        "agents/support/greet.py": "print('hello')",
        "agents/support/out.txt": "hello",
    }
    assert fixture.proposals.list_pending(fixture.workspace) == []


def test_rejecting_leaves_the_tree_unchanged_and_discards_the_working_copy(
    db_session: DBSession,
) -> None:
    sandbox = FakeSandboxPort([_wrote(("agents/support/greet.py", "print('hello')"))])
    fixture = _setup(db_session, sandbox, GREETER)
    fixture.executions.execute(fixture.session, "python greet.py")
    fixture.session_proposals.submit(fixture.workspace, fixture.user, fixture.session)

    resolved = fixture.session_proposals.reject(fixture.workspace, fixture.user, fixture.session)

    assert all(p.status is ProposalStatus.rejected for p in resolved)
    assert fixture.canonical() == GREETER
    assert fixture.working_copy() == {}


def test_approving_also_discards_the_working_copy(db_session: DBSession) -> None:
    sandbox = FakeSandboxPort([_wrote(("agents/support/greet.py", "print('hello')"))])
    fixture = _setup(db_session, sandbox, GREETER)
    fixture.executions.execute(fixture.session, "python greet.py")
    fixture.session_proposals.submit(fixture.workspace, fixture.user, fixture.session)

    fixture.session_proposals.approve(fixture.workspace, fixture.user, fixture.session)

    assert fixture.working_copy() == {}


def test_an_ended_session_takes_no_further_work(db_session: DBSession) -> None:
    fixture = _setup(db_session, FakeSandboxPort(), GREETER)
    fixture.session_proposals.submit(fixture.workspace, fixture.user, fixture.session)

    with pytest.raises(AgentSessionError):
        fixture.sessions.send_message(fixture.workspace, fixture.session, "one more thing")
    with pytest.raises(AgentSessionError):
        fixture.executions.execute(fixture.session, "ls")
    with pytest.raises(SessionProposalError):
        fixture.session_proposals.submit(fixture.workspace, fixture.user, fixture.session)


def test_a_session_proposal_can_be_superseded_by_a_manual_edit(db_session: DBSession) -> None:
    """Session proposals are ordinary proposals — the no-branching rule still holds."""
    sandbox = FakeSandboxPort([_wrote(("agents/support/greet.py", "print('hello')"))])
    fixture = _setup(db_session, sandbox, GREETER)
    fixture.executions.execute(fixture.session, "python greet.py")
    fixture.session_proposals.submit(fixture.workspace, fixture.user, fixture.session)

    fixture.proposals.propose(
        fixture.workspace, fixture.user, "agents/support/greet.py", "print('manual')"
    )

    assert fixture.session_proposals.pending(fixture.workspace, fixture.session) == []
    fixture.session_proposals.approve(fixture.workspace, fixture.user, fixture.session)
    assert fixture.canonical()["agents/support/greet.py"] == "print('ahoy')"
