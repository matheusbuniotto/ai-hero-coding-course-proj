from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from icm_platform.agent.service import AgentSessionError
from icm_platform.deps import (
    AgentSessionServiceDep,
    CodeExecutionServiceDep,
    WorkspaceAccessDep,
    WorkspaceServiceDep,
)
from icm_platform.models import AgentMessage, AgentSession, CodeExecution
from icm_platform.workspace.permissions import Permission

router = APIRouter(prefix="/workspace/agent", tags=["agent"])


class StartSessionRequest(BaseModel):
    agent_name: str


class SendMessageRequest(BaseModel):
    message: str


class ExecuteRequest(BaseModel):
    command: str


def _session_json(session: AgentSession) -> dict:
    return {
        "id": session.id,
        "workspace_id": session.workspace_id,
        "agent_name": session.agent_name,
        "created_at": session.created_at.isoformat(),
    }


def _message_json(message: AgentMessage) -> dict:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
    }


def _execution_json(execution: CodeExecution) -> dict:
    return {
        "id": execution.id,
        "command": execution.command,
        "status": execution.status,
        "exit_code": execution.exit_code,
        "stdout": execution.stdout,
        "stderr": execution.stderr,
        "produced": execution.produced,
        "created_at": execution.created_at.isoformat(),
    }


def get_session(
    session_id: int, access: WorkspaceAccessDep, agent: AgentSessionServiceDep
) -> AgentSession:
    """The session named in the path, 404 unless it belongs to the caller's workspace."""
    try:
        return agent.get_for_workspace(access.workspace, session_id)
    except AgentSessionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


SessionDep = Annotated[AgentSession, Depends(get_session)]


@router.get("/agents")
def list_agents(access: WorkspaceAccessDep, workspaces: WorkspaceServiceDep) -> list[str]:
    access.require(Permission.read)
    return workspaces.list_agents(access.workspace)


@router.post("/sessions")
def start_session(
    body: StartSessionRequest, access: WorkspaceAccessDep, agent: AgentSessionServiceDep
) -> dict:
    access.require(Permission.read)
    session = agent.start_session(access.workspace, access.user, body.agent_name)
    return _session_json(session)


@router.post("/sessions/{session_id}/messages")
def send_message(
    body: SendMessageRequest,
    session: SessionDep,
    access: WorkspaceAccessDep,
    agent: AgentSessionServiceDep,
) -> dict:
    access.require(Permission.read)
    reply = agent.send_message(access.workspace, session, body.message)
    return _message_json(reply)


@router.get("/sessions/{session_id}/messages")
def list_messages(
    session: SessionDep, access: WorkspaceAccessDep, agent: AgentSessionServiceDep
) -> list[dict]:
    access.require(Permission.read)
    return [_message_json(m) for m in agent.list_messages(session)]


@router.post("/sessions/{session_id}/executions")
def execute_code(
    body: ExecuteRequest,
    session: SessionDep,
    access: WorkspaceAccessDep,
    executions: CodeExecutionServiceDep,
) -> dict:
    """Run a command in the session's sandbox. A failed run is a 200 with `status`."""
    access.require(Permission.run)
    return _execution_json(executions.execute(session, body.command))


@router.get("/sessions/{session_id}/executions")
def list_executions(
    session: SessionDep, access: WorkspaceAccessDep, executions: CodeExecutionServiceDep
) -> list[dict]:
    access.require(Permission.read)
    return [_execution_json(e) for e in executions.list_executions(session)]


@router.get("/sessions/{session_id}/files")
def list_working_copy(
    session: SessionDep, access: WorkspaceAccessDep, executions: CodeExecutionServiceDep
) -> list[dict]:
    """The session's ephemeral working copy — never the workspace's canonical tree."""
    access.require(Permission.read)
    files = executions.list_working_copy(session)
    return [{"path": f.path, "content": f.content} for f in files]
