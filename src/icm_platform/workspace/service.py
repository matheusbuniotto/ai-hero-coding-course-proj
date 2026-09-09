from sqlmodel import Session as DBSession
from sqlmodel import select

from icm_platform.models import User, Workspace, WorkspaceFile


class WorkspaceService:
    def __init__(self, db: DBSession):
        self.db = db

    def ensure_personal_workspace(self, user: User) -> Workspace:
        assert user.id is not None
        workspace = self.db.exec(
            select(Workspace).where(Workspace.owner_user_id == user.id)
        ).first()
        if workspace is not None:
            return workspace

        workspace = Workspace(owner_user_id=user.id, name=f"{user.email}'s workspace")
        self.db.add(workspace)
        self.db.commit()
        self.db.refresh(workspace)
        return workspace

    def get_tree(self, workspace: Workspace) -> list[str]:
        """Paths of the workspace's canonical (approved) files, sorted."""
        paths = self.db.exec(
            select(WorkspaceFile.path)
            .where(WorkspaceFile.workspace_id == workspace.id)
            .order_by(WorkspaceFile.path)
        )
        return list(paths)
