import hashlib
import secrets
from datetime import UTC, datetime


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def utcnow() -> datetime:
    """Naive UTC now — SQLite drops tzinfo on roundtrip, so store/compare naive throughout."""
    return datetime.now(UTC).replace(tzinfo=None)
