from fastapi import APIRouter
from pydantic import BaseModel

from icm_platform.deps import CurrentUser, WorkspaceAccessDep, WorkspaceServiceDep
from icm_platform.models import Workspace, WorkspaceMember, WorkspaceRole
from icm_platform.workspace.permissions import Permission

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class CreateWorkspaceRequest(BaseModel):
    name: str


class InviteMemberRequest(BaseModel):
    email: str
    role: WorkspaceRole


class ForkWorkspaceRequest(BaseModel):
    name: str
    path_prefix: str | None = None


def workspace_json(workspace: Workspace, role: WorkspaceRole) -> dict:
    return {"id": workspace.id, "name": workspace.name, "kind": workspace.kind, "role": role}


def _member_json(member: WorkspaceMember) -> dict:
    return {"user_id": member.user_id, "email": member.user.email, "role": member.role}


@router.post("")
def create_workspace(
    body: CreateWorkspaceRequest, user: CurrentUser, service: WorkspaceServiceDep
) -> dict:
    workspace = service.create_team_workspace(user, body.name)
    return workspace_json(workspace, WorkspaceRole.owner)


@router.get("")
def list_workspaces(user: CurrentUser, service: WorkspaceServiceDep) -> list[dict]:
    return [workspace_json(m.workspace, m.role) for m in service.list_memberships(user)]


@router.get("/{workspace_id}/members")
def list_members(access: WorkspaceAccessDep) -> list[dict]:
    access.require(Permission.read)
    return [_member_json(m) for m in access.members()]


@router.post("/{workspace_id}/members")
def invite_member(body: InviteMemberRequest, access: WorkspaceAccessDep) -> dict:
    access.require(Permission.manage_members)
    return _member_json(access.invite_member(body.email, body.role))


@router.delete("/{workspace_id}/members/{user_id}")
def remove_member(user_id: int, access: WorkspaceAccessDep) -> dict:
    access.require(Permission.manage_members)
    access.remove_member(user_id)
    return {"removed_user_id": user_id}


@router.post("/{workspace_id}/fork")
def fork_workspace(
    workspace_id: int,
    body: ForkWorkspaceRequest,
    user: CurrentUser,
    service: WorkspaceServiceDep,
) -> dict:
    fork = service.fork_workspace(user, workspace_id, body.name, body.path_prefix)
    return workspace_json(fork, WorkspaceRole.owner)
