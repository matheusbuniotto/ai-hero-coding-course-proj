from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from icm_platform.agent.service import AgentSessionError
from icm_platform.deps import AgentSessionServiceDep, WorkspaceAccessDep
from icm_platform.models import AgentMessage, AgentSession
from icm_platform.workspace.permissions import Permission

router = APIRouter(prefix="/workspace/agent", tags=["agent"])


class SendMessageRequest(BaseModel):
    message: str


def _session_json(session: AgentSession) -> dict:
    return {
        "id": session.id,
        "workspace_id": session.workspace_id,
        "created_at": session.created_at.isoformat(),
    }


def _message_json(message: AgentMessage) -> dict:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
    }


def _get_session(
    access: WorkspaceAccessDep, agent: AgentSessionServiceDep, session_id: int
) -> AgentSession:
    try:
        return agent.get_for_workspace(access.workspace, session_id)
    except AgentSessionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/sessions")
def start_session(access: WorkspaceAccessDep, agent: AgentSessionServiceDep) -> dict:
    access.require(Permission.read)
    session = agent.start_session(access.workspace, access.user)
    return _session_json(session)


@router.post("/sessions/{session_id}/messages")
def send_message(
    session_id: int,
    body: SendMessageRequest,
    access: WorkspaceAccessDep,
    agent: AgentSessionServiceDep,
) -> dict:
    access.require(Permission.read)
    session = _get_session(access, agent, session_id)
    reply = agent.send_message(access.workspace, session, body.message)
    return _message_json(reply)


@router.get("/sessions/{session_id}/messages")
def list_messages(
    session_id: int, access: WorkspaceAccessDep, agent: AgentSessionServiceDep
) -> list[dict]:
    access.require(Permission.read)
    session = _get_session(access, agent, session_id)
    return [_message_json(m) for m in agent.list_messages(session)]
