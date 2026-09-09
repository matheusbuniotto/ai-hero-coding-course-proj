import pytest
from sqlmodel import Session as DBSession

from icm_platform.models import User, Workspace, WorkspaceKind, WorkspaceRole
from icm_platform.workspace.permissions import Permission
from icm_platform.workspace.service import WorkspaceAccessError, WorkspaceService


def _user(db_session: DBSession, email: str) -> User:
    user = User(email=email)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def service(db_session: DBSession) -> WorkspaceService:
    return WorkspaceService(db_session)


@pytest.fixture
def founder(db_session: DBSession) -> User:
    return _user(db_session, "founder@example.com")


def test_create_team_workspace_makes_creator_an_owner(
    service: WorkspaceService, founder: User
) -> None:
    workspace = service.create_team_workspace(founder, "Team Wiki")

    assert workspace.kind == WorkspaceKind.team
    assert service.role_of(workspace, founder) == WorkspaceRole.owner


def test_personal_workspace_owner_is_a_member(service: WorkspaceService, founder: User) -> None:
    workspace = service.ensure_personal_workspace(founder)

    assert workspace.kind == WorkspaceKind.personal
    assert service.role_of(workspace, founder) == WorkspaceRole.owner


def test_creating_a_team_workspace_leaves_personal_workspace_intact(
    service: WorkspaceService, founder: User
) -> None:
    personal = service.ensure_personal_workspace(founder)
    service.create_team_workspace(founder, "Team Wiki")

    assert service.ensure_personal_workspace(founder).id == personal.id


def test_invited_member_gets_the_given_role(
    service: WorkspaceService, db_session: DBSession, founder: User
) -> None:
    editor = _user(db_session, "editor@example.com")
    workspace = service.create_team_workspace(founder, "Team Wiki")

    service.invite_member(workspace, editor.email, WorkspaceRole.editor)

    assert service.role_of(workspace, editor) == WorkspaceRole.editor


def test_inviting_an_unknown_email_creates_the_user(
    service: WorkspaceService, founder: User
) -> None:
    workspace = service.create_team_workspace(founder, "Team Wiki")

    member = service.invite_member(workspace, "newcomer@example.com", WorkspaceRole.viewer)

    assert member.role == WorkspaceRole.viewer
    assert [m.user.email for m in service.list_members(workspace)] == [
        founder.email,
        "newcomer@example.com",
    ]


def test_reinviting_a_member_replaces_their_role(
    service: WorkspaceService, db_session: DBSession, founder: User
) -> None:
    member = _user(db_session, "member@example.com")
    workspace = service.create_team_workspace(founder, "Team Wiki")
    service.invite_member(workspace, member.email, WorkspaceRole.viewer)

    service.invite_member(workspace, member.email, WorkspaceRole.editor)

    assert service.role_of(workspace, member) == WorkspaceRole.editor
    assert len(service.list_members(workspace)) == 2


def test_removed_member_loses_access(
    service: WorkspaceService, db_session: DBSession, founder: User
) -> None:
    member = _user(db_session, "member@example.com")
    workspace = service.create_team_workspace(founder, "Team Wiki")
    service.invite_member(workspace, member.email, WorkspaceRole.editor)

    assert member.id is not None
    service.remove_member(workspace, member.id)

    assert service.role_of(workspace, member) is None


def test_non_member_cannot_reach_the_workspace(
    service: WorkspaceService, db_session: DBSession, founder: User
) -> None:
    outsider = _user(db_session, "outsider@example.com")
    workspace = service.create_team_workspace(founder, "Team Wiki")
    assert workspace.id is not None

    with pytest.raises(WorkspaceAccessError):
        service.get_for_user(outsider, workspace.id)


def test_viewer_cannot_propose_and_editor_cannot_approve(
    service: WorkspaceService, db_session: DBSession, founder: User
) -> None:
    viewer = _user(db_session, "viewer@example.com")
    editor = _user(db_session, "editor@example.com")
    workspace = service.create_team_workspace(founder, "Team Wiki")
    service.invite_member(workspace, viewer.email, WorkspaceRole.viewer)
    service.invite_member(workspace, editor.email, WorkspaceRole.editor)

    service.require(workspace, editor, Permission.propose)
    service.require(workspace, founder, Permission.approve)

    with pytest.raises(WorkspaceAccessError, match="viewer"):
        service.require(workspace, viewer, Permission.propose)
    with pytest.raises(WorkspaceAccessError, match="approve"):
        service.require(workspace, editor, Permission.approve)


def test_the_last_owner_cannot_be_demoted_or_removed(
    service: WorkspaceService, db_session: DBSession, founder: User
) -> None:
    editor = _user(db_session, "editor@example.com")
    workspace = service.create_team_workspace(founder, "Team Wiki")
    service.invite_member(workspace, editor.email, WorkspaceRole.editor)
    assert founder.id is not None

    with pytest.raises(WorkspaceAccessError, match="at least one owner"):
        service.invite_member(workspace, founder.email, WorkspaceRole.viewer)
    with pytest.raises(WorkspaceAccessError, match="at least one owner"):
        service.remove_member(workspace, founder.id)

    service.invite_member(workspace, editor.email, WorkspaceRole.owner)
    service.remove_member(workspace, founder.id)

    assert service.role_of(workspace, founder) is None


def test_a_workspace_created_before_memberships_existed_still_belongs_to_its_owner(
    service: WorkspaceService, db_session: DBSession, founder: User
) -> None:
    assert founder.id is not None
    legacy = Workspace(owner_user_id=founder.id, name="Legacy", kind=WorkspaceKind.personal)
    db_session.add(legacy)
    db_session.commit()

    workspace = service.ensure_personal_workspace(founder)

    assert workspace.id == legacy.id
    assert service.role_of(workspace, founder) == WorkspaceRole.owner


def test_memberships_cover_only_the_workspaces_the_user_belongs_to(
    service: WorkspaceService, db_session: DBSession, founder: User
) -> None:
    other = _user(db_session, "other@example.com")
    personal = service.ensure_personal_workspace(founder)
    team = service.create_team_workspace(founder, "Team Wiki")
    service.create_team_workspace(other, "Someone Else's Wiki")

    memberships = service.list_memberships(founder)

    assert [m.workspace.id for m in memberships] == [personal.id, team.id]
    assert {m.role for m in memberships} == {WorkspaceRole.owner}
