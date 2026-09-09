import os
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session as DBSession
from sqlmodel import SQLModel, create_engine

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./workspace.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_db_session() -> Iterator[DBSession]:
    with DBSession(engine) as session:
        yield session


DBSessionDep = Annotated[DBSession, Depends(get_db_session)]
