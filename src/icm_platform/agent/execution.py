from sqlmodel import Session as DBSession
from sqlmodel import col, select

from icm_platform.agent.lifecycle import require_open
from icm_platform.models import (
    AgentSession,
    CodeExecution,
    CodeExecutionStatus,
    SessionFile,
    Workspace,
)
from icm_platform.sandbox.ports import SandboxError, SandboxFile, SandboxPort
from icm_platform.security import utcnow
from icm_platform.workspace.service import WorkspaceService


class CodeExecutionService:
    """Runs commands for a session in a hosted sandbox, on the session's working copy.

    The working copy is ephemeral and session-scoped: it starts as a snapshot
    of the agent's canonical files and accumulates whatever executions produce,
    while the workspace's canonical tree is never written.
    """

    def __init__(self, db: DBSession, workspaces: WorkspaceService, sandbox: SandboxPort):
        self.db = db
        self.workspaces = workspaces
        self.sandbox = sandbox

    def open_working_copy(self, workspace: Workspace, session: AgentSession) -> None:
        """Snapshot the agent's canonical files into this session's working copy.

        Taken once, when the session starts, so later canonical changes can't
        leak into a session already in progress.
        """
        assert session.id is not None
        for file in self.workspaces.list_agent_files(workspace, session.agent_name):
            self.db.add(
                SessionFile(
                    session_id=session.id,
                    path=file.path,
                    content=file.content,
                    base_content=file.content,
                )
            )
        self.db.commit()

    def discard_working_copy(self, session: AgentSession) -> None:
        """Throw the session's working copy away, once its changes are resolved."""
        for file in self._session_files(session):
            self.db.delete(file)
        self.db.commit()

    def execute(self, session: AgentSession, command: str) -> CodeExecution:
        """Run `command` in the sandbox, recording the outcome even when it fails."""
        require_open(session)
        assert session.id is not None
        files = [SandboxFile(path=f.path, content=f.content) for f in self._session_files(session)]
        try:
            result = self.sandbox.run(command, files)
        except SandboxError as exc:
            return self._save(
                CodeExecution(
                    session_id=session.id,
                    command=command,
                    status=CodeExecutionStatus.errored,
                    stderr=str(exc),
                )
            )

        produced = self._apply(session, result.files)
        status = (
            CodeExecutionStatus.succeeded if result.exit_code == 0 else CodeExecutionStatus.failed
        )
        return self._save(
            CodeExecution(
                session_id=session.id,
                command=command,
                status=status,
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
                produced_paths="\n".join(produced),
            )
        )

    def list_executions(self, session: AgentSession) -> list[CodeExecution]:
        executions = self.db.exec(
            select(CodeExecution)
            .where(CodeExecution.session_id == session.id)
            .order_by(col(CodeExecution.id))
        )
        return list(executions)

    def list_working_copy(self, session: AgentSession) -> list[SessionFile]:
        """The session's ephemeral files as they stand now."""
        return self._session_files(session)

    def _apply(self, session: AgentSession, produced: list[SandboxFile]) -> list[str]:
        """Write what the run produced into the working copy only."""
        assert session.id is not None
        existing = {f.path: f for f in self._session_files(session)}
        for file in produced:
            current = existing.get(file.path)
            if current is None:
                current = SessionFile(session_id=session.id, path=file.path, content=file.content)
            else:
                current.content = file.content
                current.updated_at = utcnow()
            self.db.add(current)
        self.db.commit()
        return [f.path for f in produced]

    def _session_files(self, session: AgentSession) -> list[SessionFile]:
        files = self.db.exec(
            select(SessionFile)
            .where(SessionFile.session_id == session.id)
            .order_by(col(SessionFile.path))
        )
        return list(files)

    def _save(self, execution: CodeExecution) -> CodeExecution:
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        return execution
