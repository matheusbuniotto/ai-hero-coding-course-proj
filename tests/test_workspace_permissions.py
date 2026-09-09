import pytest

from icm_platform.models import WorkspaceRole
from icm_platform.workspace.permissions import Permission, allows

ALLOWED = {
    WorkspaceRole.owner: {
        Permission.read,
        Permission.propose,
        Permission.run,
        Permission.approve,
        Permission.manage_members,
    },
    WorkspaceRole.editor: {Permission.read, Permission.propose, Permission.run},
    WorkspaceRole.viewer: {Permission.read},
}


@pytest.mark.parametrize("role", list(WorkspaceRole))
@pytest.mark.parametrize("permission", list(Permission))
def test_role_allows_exactly_its_permissions(role: WorkspaceRole, permission: Permission) -> None:
    assert allows(role, permission) is (permission in ALLOWED[role])
