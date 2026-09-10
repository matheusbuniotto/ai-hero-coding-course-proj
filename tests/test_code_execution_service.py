from sqlmodel import Session as DBSession

from icm_platform.agent.execution import CodeExecutionService
from icm_platform.agent.service import AgentSessionService
from icm_platform.models import AgentSession, CodeExecutionStatus, User, Workspace
from icm_platform.proposals.service import ProposalService
from icm_platform.sandbox.ports import SandboxFile, SandboxResult
from icm_platform.workspace.service import WorkspaceService
from tests.fakes import FakeAgentHarnessPort, FakeSandboxPort


def _user(db_session: DBSession, email: str) -> User:
    user = User(email=email)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _approve(db_session: DBSession, workspace: Workspace, user: User, file: tuple[str, str]):
    proposals = ProposalService(db_session)
    proposal = proposals.propose(workspace, user, *file)
    assert proposal.id is not None
    proposals.approve(workspace, user, proposal.id)


def _session(
    db_session: DBSession, workspaces: WorkspaceService, workspace: Workspace, user: User
) -> AgentSession:
    sessions = AgentSessionService(db_session, workspaces, FakeAgentHarnessPort())
    return sessions.start_session(workspace, user, "support")


def test_execution_runs_on_a_copy_of_the_agents_canonical_files(db_session: DBSession) -> None:
    user = _user(db_session, "walker@example.com")
    workspaces = WorkspaceService(db_session)
    workspace = workspaces.ensure_personal_workspace(user)
    _approve(db_session, workspace, user, ("agents/support/greet.py", "print('ahoy')"))
    session = _session(db_session, workspaces, workspace, user)
    sandbox = FakeSandboxPort(
        [SandboxResult(exit_code=0, stdout="ahoy\n", stderr="", files=[])],
    )

    execution = CodeExecutionService(db_session, workspaces, sandbox).execute(
        workspace, session, "python greet.py"
    )

    assert execution.status == CodeExecutionStatus.succeeded
    assert execution.exit_code == 0
    assert execution.stdout == "ahoy\n"
    command, files = sandbox.calls[0]
    assert command == "python greet.py"
    assert [(f.path, f.content) for f in files] == [("agents/support/greet.py", "print('ahoy')")]


def test_produced_files_land_in_the_working_copy_not_the_canonical_tree(
    db_session: DBSession,
) -> None:
    user = _user(db_session, "walker@example.com")
    workspaces = WorkspaceService(db_session)
    workspace = workspaces.ensure_personal_workspace(user)
    _approve(db_session, workspace, user, ("agents/support/greet.py", "print('ahoy')"))
    session = _session(db_session, workspaces, workspace, user)
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
    executions = CodeExecutionService(db_session, workspaces, sandbox)

    execution = executions.execute(workspace, session, "python greet.py")

    assert execution.produced == ["agents/support/out.txt"]
    working_copy = {f.path: f.content for f in executions.list_working_copy(workspace, session)}
    assert working_copy["agents/support/out.txt"] == "ahoy"
    assert workspaces.get_tree(workspace) == ["agents/support/greet.py"]


def test_a_second_execution_sees_what_the_first_one_produced(db_session: DBSession) -> None:
    user = _user(db_session, "walker@example.com")
    workspaces = WorkspaceService(db_session)
    workspace = workspaces.ensure_personal_workspace(user)
    session = _session(db_session, workspaces, workspace, user)
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
    executions = CodeExecutionService(db_session, workspaces, sandbox)

    executions.execute(workspace, session, "write")
    executions.execute(workspace, session, "cat notes.txt")

    _, second_files = sandbox.calls[1]
    assert [(f.path, f.content) for f in second_files] == [("notes.txt", "first")]


def test_working_copies_are_isolated_between_sessions(db_session: DBSession) -> None:
    user = _user(db_session, "walker@example.com")
    workspaces = WorkspaceService(db_session)
    workspace = workspaces.ensure_personal_workspace(user)
    first = _session(db_session, workspaces, workspace, user)
    second = _session(db_session, workspaces, workspace, user)
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
    executions = CodeExecutionService(db_session, workspaces, sandbox)

    executions.execute(workspace, first, "write")

    assert [f.path for f in executions.list_working_copy(workspace, second)] == []


def test_a_failing_command_is_recorded_rather_than_raised(db_session: DBSession) -> None:
    user = _user(db_session, "walker@example.com")
    workspaces = WorkspaceService(db_session)
    workspace = workspaces.ensure_personal_workspace(user)
    session = _session(db_session, workspaces, workspace, user)
    sandbox = FakeSandboxPort(
        [SandboxResult(exit_code=1, stdout="", stderr="boom\n", files=[])],
    )

    execution = CodeExecutionService(db_session, workspaces, sandbox).execute(
        workspace, session, "python broken.py"
    )

    assert execution.status == CodeExecutionStatus.failed
    assert execution.exit_code == 1
    assert execution.stderr == "boom\n"


def test_a_sandbox_provider_failure_is_recorded_and_the_session_survives(
    db_session: DBSession,
) -> None:
    user = _user(db_session, "walker@example.com")
    workspaces = WorkspaceService(db_session)
    workspace = workspaces.ensure_personal_workspace(user)
    session = _session(db_session, workspaces, workspace, user)
    sandbox = FakeSandboxPort(error="provider unreachable")
    executions = CodeExecutionService(db_session, workspaces, sandbox)

    execution = executions.execute(workspace, session, "python greet.py")

    assert execution.status == CodeExecutionStatus.errored
    assert execution.exit_code is None
    assert "provider unreachable" in execution.stderr
    assert [e.id for e in executions.list_executions(session)] == [execution.id]


def test_executions_are_listed_in_order_for_the_session(db_session: DBSession) -> None:
    user = _user(db_session, "walker@example.com")
    workspaces = WorkspaceService(db_session)
    workspace = workspaces.ensure_personal_workspace(user)
    session = _session(db_session, workspaces, workspace, user)
    executions = CodeExecutionService(db_session, workspaces, FakeSandboxPort())

    executions.execute(workspace, session, "first")
    executions.execute(workspace, session, "second")

    assert [e.command for e in executions.list_executions(session)] == ["first", "second"]
