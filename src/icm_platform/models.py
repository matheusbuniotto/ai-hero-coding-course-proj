from datetime import datetime
from enum import Enum

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

from icm_platform.security import utcnow


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)


class MagicLinkToken(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    token_hash: str = Field(unique=True, index=True)
    expires_at: datetime
    consumed_at: datetime | None = None


class Session(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    token_hash: str = Field(unique=True, index=True)
    expires_at: datetime


class WorkspaceKind(str, Enum):
    personal = "personal"
    team = "team"


class WorkspaceRole(str, Enum):
    owner = "owner"
    editor = "editor"
    viewer = "viewer"


class Workspace(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    owner_user_id: int = Field(foreign_key="user.id", index=True)
    name: str
    kind: WorkspaceKind = Field(default=WorkspaceKind.personal)


class WorkspaceMember(SQLModel, table=True):
    """A user's single role on a workspace."""

    __table_args__ = (UniqueConstraint("workspace_id", "user_id"),)

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    role: WorkspaceRole

    user: User = Relationship()
    workspace: Workspace = Relationship()


class WorkspaceFile(SQLModel, table=True):
    """Canonical (approved) content of a file, keyed by workspace + path."""

    __table_args__ = (UniqueConstraint("workspace_id", "path"),)

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id", index=True)
    path: str = Field(index=True)
    content: str
    updated_at: datetime = Field(default_factory=utcnow)


class ProposalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    superseded = "superseded"


class FileProposal(SQLModel, table=True):
    """A proposed edit to a single file, awaiting approve/reject.

    A new pending proposal for the same (workspace, path) supersedes any
    existing pending one for that path — there is no branching/merge.

    `session_id` groups the proposals an agent session submitted together, so
    they can be shown as one consolidated diff and resolved in one decision.
    """

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id", index=True)
    path: str = Field(index=True)
    proposed_by_user_id: int = Field(foreign_key="user.id")
    session_id: int | None = Field(default=None, foreign_key="agentsession.id", index=True)
    base_content: str | None
    proposed_content: str
    status: ProposalStatus = Field(default=ProposalStatus.pending)
    created_at: datetime = Field(default_factory=utcnow)
    resolved_at: datetime | None = None
    resolved_by_user_id: int | None = Field(default=None, foreign_key="user.id")


class AgentSession(SQLModel, table=True):
    """A conversation between a user and their workspace agent.

    Anything the session does to files happens in its own working copy
    (`SessionFile`), never in the workspace's canonical tree.

    Ending the session submits that working copy as a proposal; an ended
    session takes no further messages or executions.
    """

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    agent_name: str
    created_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = None


class AgentMessageRole(str, Enum):
    user = "user"
    assistant = "assistant"


class AgentMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="agentsession.id", index=True)
    role: AgentMessageRole
    content: str
    created_at: datetime = Field(default_factory=utcnow)


class SessionFile(SQLModel, table=True):
    """One file of a session's ephemeral working copy.

    Seeded from the workspace's canonical files and then changed freely by
    code execution. Nothing here reaches the canonical tree without going
    through the propose/approve flow.

    `base_content` is what the file held when the working copy was taken —
    None for a file the session created — so the session's own changes can be
    told apart from what the file started as.
    """

    __table_args__ = (UniqueConstraint("session_id", "path"),)

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="agentsession.id", index=True)
    path: str = Field(index=True)
    content: str
    base_content: str | None = None
    updated_at: datetime = Field(default_factory=utcnow)

    @property
    def changed(self) -> bool:
        return self.content != self.base_content


class CodeExecutionStatus(str, Enum):
    succeeded = "succeeded"
    failed = "failed"
    errored = "errored"


class CodeExecution(SQLModel, table=True):
    """One command run in the sandbox on a session's working copy.

    `failed` means the command ran and exited non-zero; `errored` means the
    sandbox provider never ran it, in which case `exit_code` is None.
    """

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="agentsession.id", index=True)
    command: str
    status: CodeExecutionStatus
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    produced_paths: str = ""
    duration_ms: int = 0
    created_at: datetime = Field(default_factory=utcnow)

    @property
    def produced(self) -> list[str]:
        """Paths the run created or changed in the working copy."""
        return self.produced_paths.split("\n") if self.produced_paths else []

    def report(self) -> str:
        """A plain-text account of the run, for showing inside the conversation."""
        if self.status is CodeExecutionStatus.errored:
            return f"$ {self.command}\nsandbox unavailable: {self.stderr}"
        parts = [f"$ {self.command}", f"exit code: {self.exit_code}"]
        if self.stdout:
            parts.append(f"stdout:\n{self.stdout}")
        if self.stderr:
            parts.append(f"stderr:\n{self.stderr}")
        if self.produced:
            parts.append("files: " + ", ".join(self.produced))
        return "\n".join(parts)


def refusal(command: str, reason: str) -> str:
    """The same report shape as a real run, for a command that never got to run."""
    return f"$ {command}\nrefused: {reason}"
