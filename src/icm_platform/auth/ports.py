import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class EmailPort(Protocol):
    def send_magic_link(self, email: str, link: str) -> None: ...


class ConsoleEmailPort:
    """Dev-mode email port: logs the magic link instead of sending real email."""

    def send_magic_link(self, email: str, link: str) -> None:
        logger.info("Magic link for %s: %s", email, link)
