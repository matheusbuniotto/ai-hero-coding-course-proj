import pytest
from sqlmodel import Session as DBSession

from icm_platform.models import ProposalStatus, User, Workspace
from icm_platform.proposals.service import ProposalError, ProposalService
from icm_platform.workspace.service import WorkspaceService


@pytest.fixture
def user(db_session: DBSession) -> User:
    user = User(email="owner@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def workspace(db_session: DBSession, user: User) -> Workspace:
    return WorkspaceService(db_session).ensure_personal_workspace(user)


@pytest.fixture
def service(db_session: DBSession) -> ProposalService:
    return ProposalService(db_session)


def test_propose_new_file_creates_pending_proposal(
    service: ProposalService, workspace: Workspace, user: User
) -> None:
    proposal = service.propose(workspace, user, "notes.md", "hello")

    assert proposal.status == ProposalStatus.pending
    assert proposal.path == "notes.md"
    assert proposal.base_content is None
    assert proposal.proposed_content == "hello"
    assert service.get_file_content(workspace, "notes.md") is None


def test_second_proposal_for_same_path_supersedes_first(
    service: ProposalService, workspace: Workspace, user: User
) -> None:
    first = service.propose(workspace, user, "notes.md", "v1")
    second = service.propose(workspace, user, "notes.md", "v2")

    assert service.list_pending(workspace) == [second]
    refreshed_first = service.db.get(type(first), first.id)
    assert refreshed_first is not None
    assert refreshed_first.status == ProposalStatus.superseded


def test_approve_applies_proposal_to_canonical_tree(
    service: ProposalService, workspace: Workspace, user: User
) -> None:
    proposal = service.propose(workspace, user, "notes.md", "hello")
    assert proposal.id is not None

    applied = service.approve(workspace, user, proposal.id)

    assert applied.status == ProposalStatus.approved
    assert service.get_file_content(workspace, "notes.md") == "hello"
    assert "notes.md" in WorkspaceService(service.db).get_tree(workspace)


def test_reject_leaves_canonical_tree_unchanged(
    service: ProposalService, workspace: Workspace, user: User
) -> None:
    service.propose(workspace, user, "notes.md", "hello")
    initial = service.propose(workspace, user, "notes.md", "hello")
    assert initial.id is not None

    rejected = service.reject(workspace, user, initial.id)

    assert rejected.status == ProposalStatus.rejected
    assert service.get_file_content(workspace, "notes.md") is None


def test_approve_second_revision_updates_canonical_content(
    service: ProposalService, workspace: Workspace, user: User
) -> None:
    first = service.propose(workspace, user, "notes.md", "v1")
    assert first.id is not None
    service.approve(workspace, user, first.id)

    second = service.propose(workspace, user, "notes.md", "v2")
    assert second.id is not None
    assert second.base_content == "v1"
    service.approve(workspace, user, second.id)

    assert service.get_file_content(workspace, "notes.md") == "v2"


def test_history_lists_resolved_proposals_only(
    service: ProposalService, workspace: Workspace, user: User
) -> None:
    approved = service.propose(workspace, user, "a.md", "a")
    assert approved.id is not None
    service.approve(workspace, user, approved.id)
    rejected = service.propose(workspace, user, "b.md", "b")
    assert rejected.id is not None
    service.reject(workspace, user, rejected.id)
    service.propose(workspace, user, "c.md", "c")  # stays pending

    history = service.list_history(workspace)

    assert [p.path for p in history] == ["b.md", "a.md"]
    assert service.list_pending(workspace) != []


def test_approving_unknown_proposal_raises(
    service: ProposalService, workspace: Workspace, user: User
) -> None:
    with pytest.raises(ProposalError):
        service.approve(workspace, user, 999)


def test_approving_already_resolved_proposal_raises(
    service: ProposalService, workspace: Workspace, user: User
) -> None:
    proposal = service.propose(workspace, user, "notes.md", "hello")
    assert proposal.id is not None
    service.approve(workspace, user, proposal.id)

    with pytest.raises(ProposalError):
        service.approve(workspace, user, proposal.id)
