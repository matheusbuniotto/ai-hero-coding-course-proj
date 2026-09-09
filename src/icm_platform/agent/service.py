from sqlmodel import Session as DBSession
from sqlmodel import col, select

from icm_platform.agent.ports import AgentHarnessPort, ChatTurn
from icm_platform.models import AgentMessage, AgentMessageRole, AgentSession, User, Workspace
from icm_platform.workspace.service import WorkspaceService


class AgentSessionError(Exception):
    """No such session, or it doesn't belong to this workspace."""


class AgentSessionService:
    def __init__(self, db: DBSession, workspaces: WorkspaceService, harness: AgentHarnessPort):
        self.db = db
        self.workspaces = workspaces
        self.harness = harness

    def start_session(self, workspace: Workspace, user: User) -> AgentSession:
        assert workspace.id is not None
        assert user.id is not None
        session = AgentSession(workspace_id=workspace.id, user_id=user.id)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_for_workspace(self, workspace: Workspace, session_id: int) -> AgentSession:
        session = self.db.get(AgentSession, session_id)
        if session is None or session.workspace_id != workspace.id:
            raise AgentSessionError(f"No session {session_id} in this workspace")
        return session

    def list_messages(self, session: AgentSession) -> list[AgentMessage]:
        messages = self.db.exec(
            select(AgentMessage)
            .where(AgentMessage.session_id == session.id)
            .order_by(col(AgentMessage.id))
        )
        return list(messages)

    def send_message(
        self, workspace: Workspace, session: AgentSession, message: str
    ) -> AgentMessage:
        """Ask the agent for a reply, grounded in the workspace's instruction files."""
        history = [
            ChatTurn(role=m.role.value, content=m.content) for m in self.list_messages(session)
        ]
        instructions = self._instructions(workspace)

        self._store(session, AgentMessageRole.user, message)
        reply = self.harness.reply(instructions, history, message)
        return self._store(session, AgentMessageRole.assistant, reply)

    def _instructions(self, workspace: Workspace) -> str:
        files = self.workspaces.list_files(workspace)
        if not files:
            return (
                "You are a read-only assistant for a workspace that has no instruction "
                "files yet. Say so if asked about workspace content."
            )
        sections = "\n\n---\n\n".join(f"# {f.path}\n\n{f.content}" for f in files)
        return (
            "You are a read-only assistant for this workspace. Ground every answer in "
            "the instruction files below. You cannot write files or run code.\n\n" + sections
        )

    def _store(self, session: AgentSession, role: AgentMessageRole, content: str) -> AgentMessage:
        assert session.id is not None
        message = AgentMessage(session_id=session.id, role=role, content=content)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message
