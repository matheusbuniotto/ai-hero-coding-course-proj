from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from icm_platform.agent.ports import AgentHarnessPort
from icm_platform.agent.pydantic_harness import PydanticAgentHarness
from icm_platform.agent.service import AgentSessionService
from icm_platform.auth.ports import ConsoleEmailPort, EmailPort
from icm_platform.auth.service import AuthService
from icm_platform.db import DBSessionDep
from icm_platform.models import User, Workspace, WorkspaceMember, WorkspaceRole
from icm_platform.proposals.service import ProposalService
from icm_platform.workspace.permissions import Permission
from icm_platform.workspace.service import WorkspaceAccessError, WorkspaceService

SESSION_COOKIE = "session_token"


def get_email_port() -> EmailPort:
    return ConsoleEmailPort()


def get_auth_service(
    db: DBSessionDep, email_port: Annotated[EmailPort, Depends(get_email_port)]
) -> AuthService:
    return AuthService(db, email_port)


def get_workspace_service(db: DBSessionDep) -> WorkspaceService:
    return WorkspaceService(db)


def get_proposal_service(db: DBSessionDep) -> ProposalService:
    return ProposalService(db)


@lru_cache
def get_agent_harness_port() -> AgentHarnessPort:
    return PydanticAgentHarness()


def get_agent_session_service(
    db: DBSessionDep,
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
    harness: Annotated[AgentHarnessPort, Depends(get_agent_harness_port)],
) -> AgentSessionService:
    return AgentSessionService(db, workspace_service, harness)


def get_current_user(
    request: Request, auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> User | None:
    token = request.cookies.get(SESSION_COOKIE)
    if token is None:
        return None
    return auth_service.get_current_user(token)


def require_user(user: Annotated[User | None, Depends(get_current_user)]) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in")
    return user


CurrentUser = Annotated[User, Depends(require_user)]
WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]
ProposalServiceDep = Annotated[ProposalService, Depends(get_proposal_service)]
AgentSessionServiceDep = Annotated[AgentSessionService, Depends(get_agent_session_service)]


@dataclass(frozen=True)
class WorkspaceAccess:
    """One user's access to one workspace: what it holds, and what they may do in it."""

    workspace: Workspace
    user: User
    _service: WorkspaceService

    @property
    def role(self) -> WorkspaceRole:
        role = self._service.role_of(self.workspace, self.user)
        if role is None:
            raise WorkspaceAccessError(f"You are not a member of workspace {self.workspace.id}")
        return role

    def require(self, permission: Permission) -> None:
        self._service.require(self.workspace, self.user, permission)

    def tree(self) -> list[str]:
        return self._service.get_tree(self.workspace)

    def members(self) -> list[WorkspaceMember]:
        return self._service.list_members(self.workspace)

    def invite_member(self, email: str, role: WorkspaceRole) -> WorkspaceMember:
        return self._service.invite_member(self.workspace, email, role)

    def remove_member(self, user_id: int) -> None:
        self._service.remove_member(self.workspace, user_id)


def get_workspace_access(
    user: CurrentUser, service: WorkspaceServiceDep, workspace_id: int | None = None
) -> WorkspaceAccess:
    """The workspace named by `workspace_id`, or the caller's personal one when omitted."""
    workspace = (
        service.ensure_personal_workspace(user)
        if workspace_id is None
        else service.get_for_user(user, workspace_id)
    )
    return WorkspaceAccess(workspace=workspace, user=user, _service=service)


WorkspaceAccessDep = Annotated[WorkspaceAccess, Depends(get_workspace_access)]
