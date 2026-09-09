from sqlmodel import Session as DBSession
from sqlmodel import col, select

from icm_platform.models import (
    User,
    Workspace,
    WorkspaceFile,
    WorkspaceKind,
    WorkspaceMember,
    WorkspaceRole,
)
from icm_platform.workspace.permissions import Permission, allows


class WorkspaceAccessError(Exception):
    """The user may not perform this action on this workspace."""


def _org_of(email: str) -> str:
    """The org a user belongs to, approximated by their email domain."""
    return email.rsplit("@", 1)[-1].lower()


class WorkspaceService:
    def __init__(self, db: DBSession):
        self.db = db

    def ensure_personal_workspace(self, user: User) -> Workspace:
        assert user.id is not None
        workspace = self.db.exec(
            select(Workspace)
            .where(Workspace.owner_user_id == user.id)
            .where(Workspace.kind == WorkspaceKind.personal)
        ).first()
        if workspace is not None:
            self._ensure_owner_membership(workspace, user.id)
            return workspace

        return self._create(user, f"{user.email}'s workspace", WorkspaceKind.personal)

    def create_team_workspace(self, user: User, name: str) -> Workspace:
        return self._create(user, name, WorkspaceKind.team)

    def list_memberships(self, user: User) -> list[WorkspaceMember]:
        """The user's memberships, each carrying its workspace and role."""
        memberships = self.db.exec(
            select(WorkspaceMember)
            .where(WorkspaceMember.user_id == user.id)
            .order_by(col(WorkspaceMember.workspace_id))
        )
        return list(memberships)

    def get_for_user(self, user: User, workspace_id: int) -> Workspace:
        workspace = self.db.get(Workspace, workspace_id)
        if workspace is None or self.role_of(workspace, user) is None:
            raise WorkspaceAccessError(f"No workspace {workspace_id} available to you")
        return workspace

    def role_of(self, workspace: Workspace, user: User) -> WorkspaceRole | None:
        member = self._member(workspace, user)
        return member.role if member is not None else None

    def require(self, workspace: Workspace, user: User, permission: Permission) -> None:
        role = self.role_of(workspace, user)
        if role is None:
            raise WorkspaceAccessError(f"You are not a member of workspace {workspace.id}")
        if not allows(role, permission):
            raise WorkspaceAccessError(
                f"Role '{role.value}' may not {permission.value} in this workspace"
            )

    def invite_member(
        self, workspace: Workspace, email: str, role: WorkspaceRole
    ) -> WorkspaceMember:
        """Give `email` this role, registering the invitee if they have never signed in.

        Re-inviting an existing member replaces their role.
        """
        assert workspace.id is not None
        user = self.db.exec(select(User).where(User.email == email)).first()
        if user is None:
            user = User(email=email)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        assert user.id is not None

        member = self._member(workspace, user)
        if member is None:
            member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=role)
        else:
            self._guard_last_owner(workspace, member, role)
            member.role = role
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member

    def remove_member(self, workspace: Workspace, user_id: int) -> None:
        member = self._member_by_id(workspace, user_id)
        if member is None:
            raise WorkspaceAccessError(f"User {user_id} is not a member of this workspace")
        self._guard_last_owner(workspace, member, None)
        self.db.delete(member)
        self.db.commit()

    def list_members(self, workspace: Workspace) -> list[WorkspaceMember]:
        members = self.db.exec(
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace.id)
            .order_by(col(WorkspaceMember.id))
        )
        return list(members)

    def get_tree(self, workspace: Workspace) -> list[str]:
        """Paths of the workspace's canonical (approved) files, sorted."""
        paths = self.db.exec(
            select(WorkspaceFile.path)
            .where(WorkspaceFile.workspace_id == workspace.id)
            .order_by(WorkspaceFile.path)
        )
        return list(paths)

    def fork_workspace(
        self, user: User, source_workspace_id: int, name: str, path_prefix: str | None = None
    ) -> Workspace:
        """Copy a workspace (or one subfolder of it) into a new one owned by `user`.

        The fork is a one-time snapshot: nothing in it stays linked to the source.
        """
        source = self.get_for_user(user, source_workspace_id)
        owner = self.db.get(User, source.owner_user_id)
        assert owner is not None
        if _org_of(owner.email) != _org_of(user.email):
            raise WorkspaceAccessError("Cannot fork a workspace from a different org")

        fork = self._create(user, name, WorkspaceKind.team)
        assert fork.id is not None
        for file in self._files(source, path_prefix):
            self.db.add(WorkspaceFile(workspace_id=fork.id, path=file.path, content=file.content))
        self.db.commit()
        return fork

    def _files(self, workspace: Workspace, path_prefix: str | None) -> list[WorkspaceFile]:
        query = select(WorkspaceFile).where(WorkspaceFile.workspace_id == workspace.id)
        if path_prefix is not None:
            prefix = path_prefix.rstrip("/") + "/"
            query = query.where(col(WorkspaceFile.path).like(f"{prefix}%"))
        return list(self.db.exec(query))

    def _guard_last_owner(
        self, workspace: Workspace, member: WorkspaceMember, new_role: WorkspaceRole | None
    ) -> None:
        """A workspace always keeps at least one owner, so it stays manageable."""
        if member.role != WorkspaceRole.owner or new_role == WorkspaceRole.owner:
            return
        owners = [m for m in self.list_members(workspace) if m.role == WorkspaceRole.owner]
        if len(owners) == 1:
            raise WorkspaceAccessError("A workspace must keep at least one owner")

    def _ensure_owner_membership(self, workspace: Workspace, user_id: int) -> None:
        if self._member_by_id(workspace, user_id) is not None:
            return
        assert workspace.id is not None
        self.db.add(
            WorkspaceMember(workspace_id=workspace.id, user_id=user_id, role=WorkspaceRole.owner)
        )
        self.db.commit()

    def _create(self, user: User, name: str, kind: WorkspaceKind) -> Workspace:
        assert user.id is not None
        workspace = Workspace(owner_user_id=user.id, name=name, kind=kind)
        self.db.add(workspace)
        self.db.commit()
        self.db.refresh(workspace)

        self._ensure_owner_membership(workspace, user.id)
        return workspace

    def _member(self, workspace: Workspace, user: User) -> WorkspaceMember | None:
        assert user.id is not None
        return self._member_by_id(workspace, user.id)

    def _member_by_id(self, workspace: Workspace, user_id: int) -> WorkspaceMember | None:
        return self.db.exec(
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace.id)
            .where(WorkspaceMember.user_id == user_id)
        ).first()
