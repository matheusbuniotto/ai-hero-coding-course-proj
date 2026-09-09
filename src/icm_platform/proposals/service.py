from sqlmodel import Session as DBSession
from sqlmodel import select

from icm_platform.models import FileProposal, ProposalStatus, User, Workspace, WorkspaceFile
from icm_platform.security import utcnow


class ProposalError(Exception):
    pass


class ProposalService:
    def __init__(self, db: DBSession):
        self.db = db

    def get_file_content(self, workspace: Workspace, path: str) -> str | None:
        file = self._get_file(workspace, path)
        return file.content if file is not None else None

    def propose(self, workspace: Workspace, user: User, path: str, content: str) -> FileProposal:
        assert workspace.id is not None
        assert user.id is not None

        for existing in self._pending_for_path(workspace, path):
            existing.status = ProposalStatus.superseded
            existing.resolved_at = utcnow()
            existing.resolved_by_user_id = user.id
            self.db.add(existing)

        base_content = self.get_file_content(workspace, path)
        proposal = FileProposal(
            workspace_id=workspace.id,
            path=path,
            proposed_by_user_id=user.id,
            base_content=base_content,
            proposed_content=content,
        )
        self.db.add(proposal)
        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def approve(self, workspace: Workspace, user: User, proposal_id: int) -> FileProposal:
        proposal = self._get_pending(workspace, proposal_id)
        assert user.id is not None

        file = self._get_file(workspace, proposal.path)
        if file is None:
            file = WorkspaceFile(
                workspace_id=proposal.workspace_id,
                path=proposal.path,
                content=proposal.proposed_content,
            )
        else:
            file.content = proposal.proposed_content
            file.updated_at = utcnow()
        self.db.add(file)

        proposal.status = ProposalStatus.approved
        proposal.resolved_at = utcnow()
        proposal.resolved_by_user_id = user.id
        self.db.add(proposal)
        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def reject(self, workspace: Workspace, user: User, proposal_id: int) -> FileProposal:
        proposal = self._get_pending(workspace, proposal_id)
        assert user.id is not None

        proposal.status = ProposalStatus.rejected
        proposal.resolved_at = utcnow()
        proposal.resolved_by_user_id = user.id
        self.db.add(proposal)
        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def list_pending(self, workspace: Workspace) -> list[FileProposal]:
        proposals = self.db.exec(
            select(FileProposal)
            .where(FileProposal.workspace_id == workspace.id)
            .where(FileProposal.status == ProposalStatus.pending)
        )
        return sorted(proposals, key=lambda p: p.created_at)

    def list_history(self, workspace: Workspace) -> list[FileProposal]:
        proposals = self.db.exec(
            select(FileProposal)
            .where(FileProposal.workspace_id == workspace.id)
            .where(FileProposal.status != ProposalStatus.pending)
        )
        return sorted(proposals, key=lambda p: p.created_at, reverse=True)

    def _get_file(self, workspace: Workspace, path: str) -> WorkspaceFile | None:
        return self.db.exec(
            select(WorkspaceFile)
            .where(WorkspaceFile.workspace_id == workspace.id)
            .where(WorkspaceFile.path == path)
        ).first()

    def _pending_for_path(self, workspace: Workspace, path: str) -> list[FileProposal]:
        return list(
            self.db.exec(
                select(FileProposal)
                .where(FileProposal.workspace_id == workspace.id)
                .where(FileProposal.path == path)
                .where(FileProposal.status == ProposalStatus.pending)
            )
        )

    def _get_pending(self, workspace: Workspace, proposal_id: int) -> FileProposal:
        proposal = self.db.get(FileProposal, proposal_id)
        if (
            proposal is None
            or proposal.workspace_id != workspace.id
            or proposal.status != ProposalStatus.pending
        ):
            raise ProposalError(f"No pending proposal {proposal_id} in this workspace")
        return proposal
