from datetime import timedelta

from sqlmodel import Session as DBSession
from sqlmodel import select

from icm_platform.auth.service import AuthService
from icm_platform.models import MagicLinkToken
from icm_platform.security import utcnow


class FakeEmailPort:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_magic_link(self, email: str, link: str) -> None:
        self.sent.append((email, link))


def test_request_magic_link_creates_user_and_sends_email(db_session: DBSession) -> None:
    email_port = FakeEmailPort()
    service = AuthService(db_session, email_port)

    service.request_magic_link("new@example.com", "https://app.test/auth/verify")

    assert len(email_port.sent) == 1
    sent_email, link = email_port.sent[0]
    assert sent_email == "new@example.com"
    assert link.startswith("https://app.test/auth/verify?token=")


def test_verify_magic_link_signs_in_first_time_user(db_session: DBSession) -> None:
    email_port = FakeEmailPort()
    service = AuthService(db_session, email_port)
    service.request_magic_link("new@example.com", "https://app.test/auth/verify")
    token = email_port.sent[0][1].split("token=")[1]

    result = service.verify_magic_link(token)

    assert result is not None
    user, session_token = result
    assert user.email == "new@example.com"
    assert session_token
    assert service.get_current_user(session_token) is not None


def test_verify_magic_link_rejects_unknown_token(db_session: DBSession) -> None:
    service = AuthService(db_session, FakeEmailPort())
    assert service.verify_magic_link("not-a-real-token") is None


def test_verify_magic_link_rejects_reused_token(db_session: DBSession) -> None:
    email_port = FakeEmailPort()
    service = AuthService(db_session, email_port)
    service.request_magic_link("new@example.com", "https://app.test/auth/verify")
    token = email_port.sent[0][1].split("token=")[1]

    first = service.verify_magic_link(token)
    second = service.verify_magic_link(token)

    assert first is not None
    assert second is None


def test_verify_magic_link_rejects_expired_token(db_session: DBSession) -> None:
    email_port = FakeEmailPort()
    service = AuthService(db_session, email_port)
    service.request_magic_link("new@example.com", "https://app.test/auth/verify")

    link = db_session.exec(select(MagicLinkToken)).first()
    assert link is not None
    link.expires_at = utcnow() - timedelta(minutes=1)
    db_session.add(link)
    db_session.commit()

    token = email_port.sent[0][1].split("token=")[1]
    assert service.verify_magic_link(token) is None


def test_logout_invalidates_session(db_session: DBSession) -> None:
    email_port = FakeEmailPort()
    service = AuthService(db_session, email_port)
    service.request_magic_link("new@example.com", "https://app.test/auth/verify")
    token = email_port.sent[0][1].split("token=")[1]
    result = service.verify_magic_link(token)
    assert result is not None
    _user, session_token = result

    service.logout(session_token)

    assert service.get_current_user(session_token) is None
