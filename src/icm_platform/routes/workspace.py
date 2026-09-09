from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from icm_platform.deps import get_proposal_service, get_workspace_service, require_user
from icm_platform.models import FileProposal, User
from icm_platform.paths import TEMPLATES_DIR
from icm_platform.proposals.service import ProposalError, ProposalService
from icm_platform.workspace.service import WorkspaceService

router = APIRouter(prefix="/workspace", tags=["workspace"])
templates = Jinja2Templates(directory=TEMPLATES_DIR)


class ProposeFileRequest(BaseModel):
    path: str
    content: str


def _proposal_json(proposal: FileProposal) -> dict:
    return {
        "id": proposal.id,
        "path": proposal.path,
        "status": proposal.status,
        "base_content": proposal.base_content,
        "proposed_content": proposal.proposed_content,
        "created_at": proposal.created_at.isoformat(),
        "resolved_at": proposal.resolved_at.isoformat() if proposal.resolved_at else None,
    }


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


@router.post("/files/propose")
def propose_file(
    body: ProposeFileRequest,
    user: Annotated[User, Depends(require_user)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
    proposal_service: Annotated[ProposalService, Depends(get_proposal_service)],
) -> dict:
    workspace = workspace_service.ensure_personal_workspace(user)
    proposal = proposal_service.propose(workspace, user, body.path, body.content)
    return _proposal_json(proposal)


@router.get("/proposals")
def list_proposals(
    user: Annotated[User, Depends(require_user)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
    proposal_service: Annotated[ProposalService, Depends(get_proposal_service)],
) -> list[dict]:
    workspace = workspace_service.ensure_personal_workspace(user)
    return [_proposal_json(p) for p in proposal_service.list_pending(workspace)]


@router.get("/history")
def list_history(
    user: Annotated[User, Depends(require_user)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
    proposal_service: Annotated[ProposalService, Depends(get_proposal_service)],
) -> list[dict]:
    workspace = workspace_service.ensure_personal_workspace(user)
    return [_proposal_json(p) for p in proposal_service.list_history(workspace)]


@router.post("/proposals/{proposal_id}/approve")
def approve_proposal(
    proposal_id: int,
    user: Annotated[User, Depends(require_user)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
    proposal_service: Annotated[ProposalService, Depends(get_proposal_service)],
) -> dict:
    workspace = workspace_service.ensure_personal_workspace(user)
    try:
        proposal = proposal_service.approve(workspace, user, proposal_id)
    except ProposalError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _proposal_json(proposal)


@router.post("/proposals/{proposal_id}/reject")
def reject_proposal(
    proposal_id: int,
    user: Annotated[User, Depends(require_user)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
    proposal_service: Annotated[ProposalService, Depends(get_proposal_service)],
) -> dict:
    workspace = workspace_service.ensure_personal_workspace(user)
    try:
        proposal = proposal_service.reject(workspace, user, proposal_id)
    except ProposalError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _proposal_json(proposal)
