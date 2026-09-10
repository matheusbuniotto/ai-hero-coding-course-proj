from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from icm_platform.agent.lifecycle import AgentSessionError, SessionEndedError
from icm_platform.deps import (
    AgentSessionServiceDep,
    CodeExecutionServiceDep,
    SessionProposalServiceDep,
    WorkspaceAccess,
    WorkspaceAccessDep,
    WorkspaceServiceDep,
)
from icm_platform.models import (
    AgentMessage,
    AgentSession,
    CodeExecution,
    FileProposal,
    User,
    Workspace,
)
from icm_platform.proposals.session import SessionProposalError
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
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
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


def _session_proposal_json(session: AgentSession, proposals: list[FileProposal]) -> dict:
    """One session's consolidated diff: every file it changed, in one payload."""
    return {
        "session_id": session.id,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "changes": [
            {
                "proposal_id": p.id,
                "path": p.path,
                "status": p.status,
                "base_content": p.base_content,
                "proposed_content": p.proposed_content,
            }
            for p in proposals
        ],
    }


def _conflict(exc: Exception) -> HTTPException:
    """The session is in the wrong state for this — already ended, or not yet ended."""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


SessionResolver = Callable[[Workspace, User, AgentSession], list[FileProposal]]


def _resolve_session(
    resolve: SessionResolver, session: AgentSession, access: WorkspaceAccess
) -> dict:
    try:
        resolved = resolve(access.workspace, access.user, session)
    except SessionProposalError as exc:
        raise _conflict(exc) from exc
    return _session_proposal_json(session, resolved)


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
    access.require(Permission.propose)
    session = agent.start_session(access.workspace, access.user, body.agent_name)
    return _session_json(session)


@router.get("/sessions")
def list_sessions(
    agent_name: str, access: WorkspaceAccessDep, agent: AgentSessionServiceDep
) -> list[dict]:
    """This workspace's sessions with `agent_name`, most recent first."""
    access.require(Permission.read)
    return [_session_json(s) for s in agent.list_for_workspace(access.workspace, agent_name)]


@router.post("/sessions/{session_id}/messages")
def send_message(
    body: SendMessageRequest,
    session: SessionDep,
    access: WorkspaceAccessDep,
    agent: AgentSessionServiceDep,
) -> dict:
    access.require(Permission.propose)
    try:
        reply = agent.send_message(access.workspace, session, body.message)
    except SessionEndedError as exc:
        raise _conflict(exc) from exc
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
    try:
        return _execution_json(executions.execute(session, body.command))
    except SessionEndedError as exc:
        raise _conflict(exc) from exc


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


@router.post("/sessions/{session_id}/proposal")
def submit_session_proposal(
    session: SessionDep, access: WorkspaceAccessDep, session_proposals: SessionProposalServiceDep
) -> dict:
    """End the session, submitting everything it changed as one consolidated diff."""
    access.require(Permission.propose)
    try:
        submitted = session_proposals.submit(access.workspace, access.user, session)
    except SessionEndedError as exc:
        raise _conflict(exc) from exc
    return _session_proposal_json(session, submitted)


@router.get("/sessions/{session_id}/proposal")
def get_session_proposal(
    session: SessionDep, access: WorkspaceAccessDep, session_proposals: SessionProposalServiceDep
) -> dict:
    """The session's submitted diff, and where each of its files stands."""
    access.require(Permission.read)
    return _session_proposal_json(session, session_proposals.submitted(access.workspace, session))


@router.post("/sessions/{session_id}/proposal/approve")
def approve_session_proposal(
    session: SessionDep, access: WorkspaceAccessDep, session_proposals: SessionProposalServiceDep
) -> dict:
    """Apply the session's whole diff — the explicit confirm, even in a solo workspace."""
    access.require(Permission.approve)
    return _resolve_session(session_proposals.approve, session, access)


@router.post("/sessions/{session_id}/proposal/reject")
def reject_session_proposal(
    session: SessionDep, access: WorkspaceAccessDep, session_proposals: SessionProposalServiceDep
) -> dict:
    """Drop the session's whole diff and its working copy, leaving the tree unchanged."""
    access.require(Permission.approve)
    return _resolve_session(session_proposals.reject, session, access)
