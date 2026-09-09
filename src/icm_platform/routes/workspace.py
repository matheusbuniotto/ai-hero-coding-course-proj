from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from icm_platform.deps import get_workspace_service, require_user
from icm_platform.models import User
from icm_platform.paths import TEMPLATES_DIR
from icm_platform.workspace.service import WorkspaceService

router = APIRouter(prefix="/workspace", tags=["workspace"])
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("", response_class=HTMLResponse)
def view_workspace(
    request: Request,
    user: Annotated[User, Depends(require_user)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> HTMLResponse:
    workspace = workspace_service.ensure_personal_workspace(user)
    tree = workspace_service.get_tree(workspace)
    return templates.TemplateResponse(
        request, "workspace.html", {"workspace": workspace, "tree": tree}
    )


@router.get("/api")
def get_workspace_json(
    user: Annotated[User, Depends(require_user)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> dict:
    workspace = workspace_service.ensure_personal_workspace(user)
    tree = workspace_service.get_tree(workspace)
    return {"id": workspace.id, "name": workspace.name, "tree": tree}
