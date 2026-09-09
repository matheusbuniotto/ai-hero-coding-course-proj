from sqlmodel import Session as DBSession

from icm_platform.models import User
from icm_platform.workspace.service import WorkspaceService


def test_ensure_personal_workspace_creates_once(db_session: DBSession) -> None:
    user = User(email="new@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    service = WorkspaceService(db_session)

    first = service.ensure_personal_workspace(user)
    second = service.ensure_personal_workspace(user)

    assert first.id == second.id
    assert first.owner_user_id == user.id


def test_new_workspace_tree_is_empty(db_session: DBSession) -> None:
    user = User(email="new@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    service = WorkspaceService(db_session)

    workspace = service.ensure_personal_workspace(user)

    assert service.get_tree(workspace) == []
