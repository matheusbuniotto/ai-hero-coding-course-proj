from datetime import timedelta

from sqlmodel import Session as DBSession
from sqlmodel import select

from icm_platform.auth.ports import EmailPort
from icm_platform.models import MagicLinkToken, User
from icm_platform.models import Session as AppSession
from icm_platform.security import generate_token, hash_token, utcnow

MAGIC_LINK_TTL = timedelta(minutes=15)
SESSION_TTL = timedelta(days=30)


class AuthService:
    def __init__(self, db: DBSession, email_port: EmailPort):
        self.db = db
        self.email_port = email_port

    def request_magic_link(self, email: str, verify_url: str) -> None:
        user = self._get_or_create_user(email)
        assert user.id is not None

        token = generate_token()
        self.db.add(
            MagicLinkToken(
                user_id=user.id,
                token_hash=hash_token(token),
                expires_at=utcnow() + MAGIC_LINK_TTL,
            )
        )
        self.db.commit()

        self.email_port.send_magic_link(email, f"{verify_url}?token={token}")

    def dev_login(self, email: str) -> tuple[User, str]:
        """Dev-only: sign in as `email` straight away, skipping the magic-link round-trip.

        Callers must gate this behind the dev-auth flag themselves — this method
        has no opinion on whether it is safe to expose.
        """
        user = self._get_or_create_user(email)
        assert user.id is not None
        return user, self._start_session(user.id)

    def verify_magic_link(self, token: str) -> tuple[User, str] | None:
        link = self.db.exec(
            select(MagicLinkToken).where(MagicLinkToken.token_hash == hash_token(token))
        ).first()
        if link is None or link.consumed_at is not None:
            return None
        if link.expires_at < utcnow():
            return None

        link.consumed_at = utcnow()
        self.db.add(link)
        self.db.commit()

        user = self.db.get(User, link.user_id)
        assert user is not None
        return user, self._start_session(link.user_id)

    def get_current_user(self, session_token: str) -> User | None:
        session = self.db.exec(
            select(AppSession).where(AppSession.token_hash == hash_token(session_token))
        ).first()
        if session is None or session.expires_at < utcnow():
            return None
        return self.db.get(User, session.user_id)

    def logout(self, session_token: str) -> None:
        session = self.db.exec(
            select(AppSession).where(AppSession.token_hash == hash_token(session_token))
        ).first()
        if session is not None:
            self.db.delete(session)
            self.db.commit()

    def _get_or_create_user(self, email: str) -> User:
        user = self.db.exec(select(User).where(User.email == email)).first()
        if user is None:
            user = User(email=email)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        return user

    def _start_session(self, user_id: int) -> str:
        session_token = generate_token()
        self.db.add(
            AppSession(
                user_id=user_id,
                token_hash=hash_token(session_token),
                expires_at=utcnow() + SESSION_TTL,
            )
        )
        self.db.commit()
        return session_token
