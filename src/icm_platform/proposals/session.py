from collections.abc import Callable

from sqlmodel import Session as DBSession

from icm_platform.agent.execution import CodeExecutionService
from icm_platform.agent.lifecycle import require_open
from icm_platform.models import AgentSession, FileProposal, ProposalStatus, User, Workspace
from icm_platform.proposals.service import ProposalService
from icm_platform.security import utcnow

Resolver = Callable[[Workspace, User, int], FileProposal]


class SessionProposalError(Exception):
    """The session's diff cannot be resolved as it stands."""


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
        require_open(session)

        submitted = []
        for file in self.executions.list_working_copy(session):
            if not file.changed:
                continue
            proposal = self.proposals.propose(workspace, user, file.path, file.content)
            # `propose` has no room for a session, so the tag goes on afterwards.
            proposal.session_id = session.id
            self.db.add(proposal)
            submitted.append(proposal)

        session.ended_at = utcnow()
        self.db.add(session)
        self.db.commit()
        return submitted

    def submitted(self, workspace: Workspace, session: AgentSession) -> list[FileProposal]:
        """The session's diff: what it proposed, and where each file stands now."""
        assert session.id is not None
        return self.proposals.list_for_session(workspace, session.id)

    def approve(
        self, workspace: Workspace, user: User, session: AgentSession
    ) -> list[FileProposal]:
        """Apply the session's diff to the canonical tree — all of it, or none of it."""
        self._require_submitted(session)
        if any(p.status is not ProposalStatus.pending for p in self.submitted(workspace, session)):
            raise SessionProposalError(
                f"Part of session {session.id}'s diff was already resolved or superseded, "
                f"so approving the rest would apply half a change"
            )
        return self._resolve(self.proposals.approve, workspace, user, session)

    def reject(self, workspace: Workspace, user: User, session: AgentSession) -> list[FileProposal]:
        """Leave the canonical tree alone and throw the session's work away."""
        self._require_submitted(session)
        return self._resolve(self.proposals.reject, workspace, user, session)

    def _require_submitted(self, session: AgentSession) -> None:
        if session.ended_at is None:
            raise SessionProposalError(f"Session {session.id} has not been submitted yet")

    def _resolve(
        self, resolve: Resolver, workspace: Workspace, user: User, session: AgentSession
    ) -> list[FileProposal]:
        resolved = []
        for proposal in self.submitted(workspace, session):
            if proposal.status is not ProposalStatus.pending:
                continue
            assert proposal.id is not None
            resolved.append(resolve(workspace, user, proposal.id))
        self.executions.discard_working_copy(session)
        return resolved
