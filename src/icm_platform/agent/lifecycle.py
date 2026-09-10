from icm_platform.models import AgentSession


class AgentSessionError(Exception):
    """No such session, or it doesn't belong to this workspace."""


class SessionEndedError(Exception):
    """The session has already submitted its changes, so it takes no more work."""


def require_open(session: AgentSession) -> None:
    """Guard work that only makes sense before the session's changes are submitted."""
    if session.ended_at is not None:
        raise SessionEndedError(f"Session {session.id} has ended")
