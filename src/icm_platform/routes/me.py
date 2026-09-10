from fastapi import APIRouter

from icm_platform.deps import CurrentUser, WorkspaceServiceDep
from icm_platform.routes.workspaces import memberships_json

router = APIRouter(tags=["me"])


@router.get("/me")
def get_me(user: CurrentUser, service: WorkspaceServiceDep) -> dict:
    """Everything the UI shell needs to boot: who is signed in, and where they may go."""
    service.ensure_personal_workspace(user)
    return {
        "user": {"id": user.id, "email": user.email},
        "workspaces": memberships_json(user, service),
    }
