from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class ChatTurn:
    """One past turn of a conversation, independent of any model library's message types."""

    role: Literal["user", "assistant"]
    content: str


class AgentHarnessPort(Protocol):
    """Swappable seam to whatever drives the conversation (Pydantic AI, a fake, ...).

    Implementations must be read-only: no file writes, no code execution.
    """

    def reply(self, instructions: str, history: list[ChatTurn], message: str) -> str: ...
