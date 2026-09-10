from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class ChatTurn:
    """One past turn of a conversation, independent of any model library's message types."""

    role: Literal["user", "assistant"]
    content: str


class CodeRunner(Protocol):
    """Runs one command in the session's sandbox and reports the outcome as text.

    Never raises: a refused, failed, or unavailable run comes back as a message
    the harness can show the user and keep talking.
    """

    def __call__(self, command: str) -> str: ...


class AgentHarnessPort(Protocol):
    """Swappable seam to whatever drives the conversation (Pydantic AI, a fake, ...).

    Implementations may not write files. The only way to run code is `run_code`,
    which goes to a hosted sandbox and touches nothing but the session's
    ephemeral working copy; when it is None, the session is read-only.
    """

    def reply(
        self,
        instructions: str,
        history: list[ChatTurn],
        message: str,
        run_code: CodeRunner | None = None,
    ) -> str: ...
