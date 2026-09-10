from sqlmodel import Session as DBSession
from sqlmodel import col, select

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


def summarize(execution: CodeExecution) -> str:
    """A plain-text account of a run, for showing inside the conversation."""
    if execution.status is CodeExecutionStatus.errored:
        return f"$ {execution.command}\nsandbox unavailable: {execution.stderr}"
    parts = [f"$ {execution.command}", f"exit code: {execution.exit_code}"]
    if execution.stdout:
        parts.append(f"stdout:\n{execution.stdout}")
    if execution.stderr:
        parts.append(f"stderr:\n{execution.stderr}")
    if execution.produced:
        parts.append("files: " + ", ".join(execution.produced))
    return "\n".join(parts)


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

    def execute(self, workspace: Workspace, session: AgentSession, command: str) -> CodeExecution:
        """Run `command` in the sandbox, recording the outcome even when it fails."""
        assert session.id is not None
        files = self._working_copy(workspace, session)
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

    def list_working_copy(self, workspace: Workspace, session: AgentSession) -> list[SessionFile]:
        """The session's ephemeral files, seeding them from the canonical tree if needed."""
        self._working_copy(workspace, session)
        return self._session_files(session)

    def _working_copy(self, workspace: Workspace, session: AgentSession) -> list[SandboxFile]:
        files = self._session_files(session)
        if not files:
            files = self._seed(workspace, session)
        return [SandboxFile(path=f.path, content=f.content) for f in files]

    def _seed(self, workspace: Workspace, session: AgentSession) -> list[SessionFile]:
        """Snapshot the agent's canonical files into this session's working copy."""
        assert session.id is not None
        canonical = self.workspaces.list_agent_files(workspace, session.agent_name)
        for file in canonical:
            self.db.add(SessionFile(session_id=session.id, path=file.path, content=file.content))
        self.db.commit()
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
