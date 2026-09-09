from icm_platform.agent.ports import ChatTurn


class FakeEmailPort:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_magic_link(self, email: str, link: str) -> None:
        self.sent.append((email, link))


class FakeAgentHarnessPort:
    """Deterministic stand-in for `AgentHarnessPort`.

    Echoes the instructions it was given back into the reply, so tests can
    verify the agent's response is grounded in the workspace's instruction
    files without ever calling a real model.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[ChatTurn], str]] = []

    def reply(self, instructions: str, history: list[ChatTurn], message: str) -> str:
        self.calls.append((instructions, list(history), message))
        return f"echo(turn={len(history) // 2 + 1}, message={message!r}): {instructions}"
