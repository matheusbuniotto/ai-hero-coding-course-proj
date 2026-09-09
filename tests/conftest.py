from collections.abc import Callable, Iterator
from contextlib import ExitStack

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session as DBSession
from sqlmodel import SQLModel, create_engine
from sqlmodel.pool import StaticPool

from icm_platform.app import create_app
from icm_platform.db import get_db_session
from icm_platform.deps import get_email_port
from tests.fakes import FakeEmailPort


@pytest.fixture
def db_session() -> Iterator[DBSession]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with DBSession(engine) as session:
        yield session


@pytest.fixture
def email_port() -> FakeEmailPort:
    return FakeEmailPort()


@pytest.fixture
def client_factory(
    db_session: DBSession, email_port: FakeEmailPort
) -> Iterator[Callable[[], TestClient]]:
    """Builds independent clients (separate cookie jars) over one shared database."""
    with ExitStack() as stack:

        def make_client() -> TestClient:
            app = create_app()
            app.dependency_overrides[get_db_session] = lambda: db_session
            app.dependency_overrides[get_email_port] = lambda: email_port
            return stack.enter_context(TestClient(app))

        yield make_client


@pytest.fixture
def client(client_factory: Callable[[], TestClient]) -> TestClient:
    return client_factory()


def sign_in(client: TestClient, email_port: FakeEmailPort, email: str) -> None:
    client.post("/auth/magic-link", data={"email": email})
    token = email_port.sent[-1][1].split("token=")[1]
    client.get(f"/auth/verify?token={token}", follow_redirects=False)
