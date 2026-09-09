from enum import Enum

from icm_platform.models import WorkspaceRole


class Permission(str, Enum):
    read = "read"
    propose = "propose"
    run = "run"
    approve = "approve"
    manage_members = "manage_members"


ROLE_PERMISSIONS: dict[WorkspaceRole, frozenset[Permission]] = {
    WorkspaceRole.owner: frozenset(Permission),
    WorkspaceRole.editor: frozenset({Permission.read, Permission.propose, Permission.run}),
    WorkspaceRole.viewer: frozenset({Permission.read}),
}


def allows(role: WorkspaceRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[role]
