from icm_platform.models import AgentSession


class AgentSessionError(Exception):
    """No such session, it doesn't belong to this workspace, or it has already ended."""


def require_open(session: AgentSession) -> None:
    """Guard work that only makes sense before the session's changes are submitted."""
    if session.ended_at is not None:
        raise AgentSessionError(f"Session {session.id} has ended")
