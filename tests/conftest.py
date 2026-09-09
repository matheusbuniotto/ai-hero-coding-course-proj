from collections.abc import Iterator

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
def client(db_session: DBSession, email_port: FakeEmailPort) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_email_port] = lambda: email_port
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
