from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from icm_platform.auth.ports import ConsoleEmailPort, EmailPort
from icm_platform.auth.service import AuthService
from icm_platform.db import DBSessionDep
from icm_platform.models import User
from icm_platform.proposals.service import ProposalService
from icm_platform.workspace.service import WorkspaceService

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
