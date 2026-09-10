from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SandboxFile:
    """One file in a sandbox working copy, independent of any provider's API."""

    path: str
    content: str


@dataclass(frozen=True)
class SandboxResult:
    """What one command left behind: its output, and the files it created or changed."""

    exit_code: int
    stdout: str
    stderr: str
    files: list[SandboxFile]


class SandboxError(Exception):
    """The sandbox provider could not run the command at all (no result to report)."""


class SandboxPort(Protocol):
    """Swappable seam to a hosted sandbox provider (or a fake).

    Implementations must run the command off host infrastructure, on an
    ephemeral copy of `files`, and must never touch a workspace's canonical
    tree. A command that runs and fails returns a non-zero `exit_code`; only a
    provider-level failure raises `SandboxError`.
    """

    def run(self, command: str, files: list[SandboxFile]) -> SandboxResult: ...


class UnavailableSandbox:
    """Default `SandboxPort` for deployments with no provider configured.

    Refuses every run rather than falling back to host execution.
    """

    def run(self, command: str, files: list[SandboxFile]) -> SandboxResult:
        raise SandboxError("No sandbox provider is configured for this deployment")
