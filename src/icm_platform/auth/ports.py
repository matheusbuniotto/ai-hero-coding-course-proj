from typing import Protocol


class EmailPort(Protocol):
    def send_magic_link(self, email: str, link: str) -> None: ...


class ConsoleEmailPort:
    """Dev-mode email port: prints the magic link instead of sending real email."""

    def send_magic_link(self, email: str, link: str) -> None:
        print(f"Magic link for {email}: {link}", flush=True)
