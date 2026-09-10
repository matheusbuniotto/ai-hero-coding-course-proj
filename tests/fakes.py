from icm_platform.agent.ports import ChatTurn, CodeRunner
from icm_platform.sandbox.ports import SandboxError, SandboxFile, SandboxResult


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

    def __init__(self, run_commands: list[str] | None = None) -> None:
        self.calls: list[tuple[str, list[ChatTurn], str]] = []
        self.run_commands = run_commands or []

    def reply(
        self,
        instructions: str,
        history: list[ChatTurn],
        message: str,
        run_code: CodeRunner | None = None,
    ) -> str:
        self.calls.append((instructions, list(history), message))
        reply = f"echo(turn={len(history) // 2 + 1}, message={message!r}): {instructions}"
        if run_code is not None:
            for command in self.run_commands:
                reply += f"\n\n{run_code(command)}"
        return reply


def wrote(*files: tuple[str, str]) -> SandboxResult:
    """A successful sandbox run that wrote these `(path, content)` pairs."""
    return SandboxResult(
        exit_code=0,
        stdout="",
        stderr="",
        files=[SandboxFile(path=path, content=content) for path, content in files],
    )


class FakeSandboxPort:
    """Deterministic stand-in for `SandboxPort` — never calls a hosted provider.

    Replays scripted results (or raises a scripted provider failure) and records
    the working copy it was handed, so tests can check what the sandbox saw.
    """

    def __init__(
        self, results: list[SandboxResult] | None = None, error: str | None = None
    ) -> None:
        self.calls: list[tuple[str, list[SandboxFile]]] = []
        self.results = results or []
        self.error = error

    def run(self, command: str, files: list[SandboxFile]) -> SandboxResult:
        self.calls.append((command, list(files)))
        if self.error is not None:
            raise SandboxError(self.error)
        if self.results:
            return self.results.pop(0)
        return SandboxResult(exit_code=0, stdout=f"ran {command}", stderr="", files=[])
