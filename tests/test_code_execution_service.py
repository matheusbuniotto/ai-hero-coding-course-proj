from dataclasses import dataclass

from sqlmodel import Session as DBSession

from icm_platform.agent.execution import CodeExecutionService
from icm_platform.agent.service import AgentSessionService
from icm_platform.models import AgentSession, CodeExecutionStatus, User, Workspace
from icm_platform.proposals.service import ProposalService
from icm_platform.sandbox.ports import SandboxFile, SandboxResult
from icm_platform.workspace.service import WorkspaceService
from tests.fakes import FakeAgentHarnessPort, FakeSandboxPort

GREETER = {"agents/support/greet.py": "print('ahoy')"}


@dataclass
class _Fixture:
    """A signed-in user with one agent session, ready to run code."""

    user: User
    workspaces: WorkspaceService
    workspace: Workspace
    sessions: AgentSessionService
    executions: CodeExecutionService
    session: AgentSession

    def open_session(self) -> AgentSession:
        return self.sessions.start_session(self.workspace, self.user, "support")


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
        session=sessions.start_session(workspace, user, "support"),
    )


def test_execution_runs_on_a_copy_of_the_agents_canonical_files(db_session: DBSession) -> None:
    sandbox = FakeSandboxPort([SandboxResult(exit_code=0, stdout="ahoy\n", stderr="", files=[])])
    fixture = _setup(db_session, sandbox, GREETER)

    execution = fixture.executions.execute(fixture.session, "python greet.py")

    assert execution.status == CodeExecutionStatus.succeeded
    assert execution.exit_code == 0
    assert execution.stdout == "ahoy\n"
    command, files = sandbox.calls[0]
    assert command == "python greet.py"
    assert [(f.path, f.content) for f in files] == [("agents/support/greet.py", "print('ahoy')")]


def test_the_working_copy_is_taken_when_the_session_starts(db_session: DBSession) -> None:
    """Later canonical changes must not leak into a session already in progress."""
    sandbox = FakeSandboxPort()
    fixture = _setup(db_session, sandbox, GREETER)
    proposals = ProposalService(db_session)
    proposal = proposals.propose(
        fixture.workspace, fixture.user, "agents/support/greet.py", "print('changed')"
    )
    assert proposal.id is not None
    proposals.approve(fixture.workspace, fixture.user, proposal.id)

    fixture.executions.execute(fixture.session, "python greet.py")

    _, files = sandbox.calls[0]
    assert [f.content for f in files] == ["print('ahoy')"]


def test_produced_files_land_in_the_working_copy_not_the_canonical_tree(
    db_session: DBSession,
) -> None:
    sandbox = FakeSandboxPort(
        [
            SandboxResult(
                exit_code=0,
                stdout="",
                stderr="",
                files=[SandboxFile(path="agents/support/out.txt", content="ahoy")],
            )
        ]
    )
    fixture = _setup(db_session, sandbox, GREETER)

    execution = fixture.executions.execute(fixture.session, "python greet.py")

    assert execution.produced == ["agents/support/out.txt"]
    working_copy = {
        f.path: f.content for f in fixture.executions.list_working_copy(fixture.session)
    }
    assert working_copy["agents/support/out.txt"] == "ahoy"
    assert fixture.workspaces.get_tree(fixture.workspace) == ["agents/support/greet.py"]


def test_a_second_execution_sees_what_the_first_one_produced(db_session: DBSession) -> None:
    sandbox = FakeSandboxPort(
        [
            SandboxResult(
                exit_code=0,
                stdout="",
                stderr="",
                files=[SandboxFile(path="notes.txt", content="first")],
            ),
            SandboxResult(exit_code=0, stdout="first", stderr="", files=[]),
        ]
    )
    fixture = _setup(db_session, sandbox)

    fixture.executions.execute(fixture.session, "write")
    fixture.executions.execute(fixture.session, "cat notes.txt")

    _, second_files = sandbox.calls[1]
    assert [(f.path, f.content) for f in second_files] == [("notes.txt", "first")]


def test_working_copies_are_isolated_between_sessions(db_session: DBSession) -> None:
    sandbox = FakeSandboxPort(
        [
            SandboxResult(
                exit_code=0,
                stdout="",
                stderr="",
                files=[SandboxFile(path="notes.txt", content="first")],
            )
        ]
    )
    fixture = _setup(db_session, sandbox)
    other = fixture.open_session()

    fixture.executions.execute(fixture.session, "write")

    assert [f.path for f in fixture.executions.list_working_copy(other)] == []


def test_a_failing_command_is_recorded_rather_than_raised(db_session: DBSession) -> None:
    sandbox = FakeSandboxPort([SandboxResult(exit_code=1, stdout="", stderr="boom\n", files=[])])
    fixture = _setup(db_session, sandbox)

    execution = fixture.executions.execute(fixture.session, "python broken.py")

    assert execution.status == CodeExecutionStatus.failed
    assert execution.exit_code == 1
    assert execution.stderr == "boom\n"
    assert "exit code: 1" in execution.report()


def test_a_sandbox_provider_failure_is_recorded_and_the_session_survives(
    db_session: DBSession,
) -> None:
    fixture = _setup(db_session, FakeSandboxPort(error="provider unreachable"))

    execution = fixture.executions.execute(fixture.session, "python greet.py")

    assert execution.status == CodeExecutionStatus.errored
    assert execution.exit_code is None
    assert "provider unreachable" in execution.stderr
    assert [e.id for e in fixture.executions.list_executions(fixture.session)] == [execution.id]


def test_executions_are_listed_in_order_for_the_session(db_session: DBSession) -> None:
    fixture = _setup(db_session, FakeSandboxPort())

    fixture.executions.execute(fixture.session, "first")
    fixture.executions.execute(fixture.session, "second")

    assert [e.command for e in fixture.executions.list_executions(fixture.session)] == [
        "first",
        "second",
    ]
