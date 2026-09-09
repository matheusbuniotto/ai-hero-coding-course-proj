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
    """

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id", index=True)
    path: str = Field(index=True)
    proposed_by_user_id: int = Field(foreign_key="user.id")
    base_content: str | None
    proposed_content: str
    status: ProposalStatus = Field(default=ProposalStatus.pending)
    created_at: datetime = Field(default_factory=utcnow)
    resolved_at: datetime | None = None
    resolved_by_user_id: int | None = Field(default=None, foreign_key="user.id")
