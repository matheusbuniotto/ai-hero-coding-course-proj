from collections.abc import Callable

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from icm_platform.deps import ProposalServiceDep, WorkspaceAccess, WorkspaceAccessDep
from icm_platform.models import FileProposal, User, Workspace
from icm_platform.paths import TEMPLATES_DIR
from icm_platform.proposals.service import ProposalError
from icm_platform.routes.workspaces import workspace_json
from icm_platform.workspace.permissions import Permission

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
def view_workspace(request: Request, access: WorkspaceAccessDep) -> HTMLResponse:
    access.require(Permission.read)
    return templates.TemplateResponse(
        request,
        "workspace.html",
        {"workspace": access.workspace, "role": access.role, "tree": access.tree()},
    )


@router.get("/api")
def get_workspace_json(access: WorkspaceAccessDep) -> dict:
    access.require(Permission.read)
    return workspace_json(access.workspace, access.role) | {
        "agents": access.agents(),
        "tree": access.tree(),
    }


@router.post("/files/propose")
def propose_file(
    body: ProposeFileRequest, access: WorkspaceAccessDep, proposals: ProposalServiceDep
) -> dict:
    access.require(Permission.propose)
    proposal = proposals.propose(access.workspace, access.user, body.path, body.content)
    return _proposal_json(proposal)


@router.get("/proposals")
def list_proposals(access: WorkspaceAccessDep, proposals: ProposalServiceDep) -> list[dict]:
    access.require(Permission.read)
    return [_proposal_json(p) for p in proposals.list_pending(access.workspace)]


@router.get("/history")
def list_history(access: WorkspaceAccessDep, proposals: ProposalServiceDep) -> list[dict]:
    access.require(Permission.read)
    return [_proposal_json(p) for p in proposals.list_history(access.workspace)]


@router.post("/proposals/{proposal_id}/approve")
def approve_proposal(
    proposal_id: int, access: WorkspaceAccessDep, proposals: ProposalServiceDep
) -> dict:
    access.require(Permission.approve)
    return _resolve(proposals.approve, access, proposal_id)


@router.post("/proposals/{proposal_id}/reject")
def reject_proposal(
    proposal_id: int, access: WorkspaceAccessDep, proposals: ProposalServiceDep
) -> dict:
    access.require(Permission.approve)
    return _resolve(proposals.reject, access, proposal_id)


Resolver = Callable[[Workspace, User, int], FileProposal]


def _resolve(resolve: Resolver, access: WorkspaceAccess, proposal_id: int) -> dict:
    try:
        proposal = resolve(access.workspace, access.user, proposal_id)
    except ProposalError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _proposal_json(proposal)
