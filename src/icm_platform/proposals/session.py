from collections.abc import Callable

from sqlmodel import Session as DBSession

from icm_platform.agent.execution import CodeExecutionService
from icm_platform.models import AgentSession, FileProposal, User, Workspace
from icm_platform.proposals.service import ProposalService
from icm_platform.security import utcnow

Resolver = Callable[[Workspace, User, int], FileProposal]


class SessionProposalError(Exception):
    """The session's changes cannot be submitted or resolved right now."""


class SessionProposalService:
    """Submits everything an agent session changed as one consolidated proposal.

    The session's working copy never reaches the canonical tree on its own:
    ending the session turns each file it changed into an ordinary
    `FileProposal`, tagged with the session so the whole set is shown as one
    diff and approved or rejected in one decision. Edits the agent made to its
    own instruction files are in there like any other file — a human watching
    the live session is not a substitute for approving.
    """

    def __init__(self, db: DBSession, proposals: ProposalService, executions: CodeExecutionService):
        self.db = db
        self.proposals = proposals
        self.executions = executions

    def submit(self, workspace: Workspace, user: User, session: AgentSession) -> list[FileProposal]:
        """End the session and propose every file its working copy changed."""
        if session.ended_at is not None:
            raise SessionProposalError(f"Session {session.id} has already been submitted")

        submitted = []
        for file in self.executions.list_working_copy(session):
            if not file.changed:
                continue
            proposal = self.proposals.propose(workspace, user, file.path, file.content)
            proposal.session_id = session.id
            self.db.add(proposal)
            submitted.append(proposal)

        session.ended_at = utcnow()
        self.db.add(session)
        self.db.commit()
        return submitted

    def pending(self, workspace: Workspace, session: AgentSession) -> list[FileProposal]:
        """The session's still-undecided proposals, oldest first."""
        return [p for p in self.proposals.list_pending(workspace) if p.session_id == session.id]

    def approve(
        self, workspace: Workspace, user: User, session: AgentSession
    ) -> list[FileProposal]:
        """Apply the whole submitted diff to the canonical tree."""
        return self._resolve(self.proposals.approve, workspace, user, session)

    def reject(self, workspace: Workspace, user: User, session: AgentSession) -> list[FileProposal]:
        """Leave the canonical tree alone and throw the session's work away."""
        return self._resolve(self.proposals.reject, workspace, user, session)

    def _resolve(
        self, resolve: Resolver, workspace: Workspace, user: User, session: AgentSession
    ) -> list[FileProposal]:
        if session.ended_at is None:
            raise SessionProposalError(f"Session {session.id} has not been submitted yet")

        resolved = []
        for proposal in self.pending(workspace, session):
            assert proposal.id is not None
            resolved.append(resolve(workspace, user, proposal.id))
        self.executions.discard_working_copy(session)
        return resolved
