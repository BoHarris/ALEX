from __future__ import annotations

from dataclasses import dataclass


ROLE_USER = "user"
ROLE_AUDITOR = "auditor"
ROLE_ORG_ADMIN = "organization_admin"
ROLE_SECURITY_ADMIN = "security_admin"

ROLE_ALIASES = {
    "member": ROLE_USER,
    "user": ROLE_USER,
    "auditor": ROLE_AUDITOR,
    "admin": ROLE_ORG_ADMIN,
    "org_admin": ROLE_ORG_ADMIN,
    "organization_admin": ROLE_ORG_ADMIN,
    "security_admin": ROLE_SECURITY_ADMIN,
}


@dataclass(frozen=True)
class RolePermissions:
    can_access_admin: bool
    can_manage_users: bool
    can_view_audit_logs: bool
    can_change_system_config: bool
    can_access_security_dashboard: bool


def normalize_role(role_value: str | None) -> str:
    return ROLE_ALIASES.get((role_value or "").strip().lower(), ROLE_USER)


def get_role_permissions(role_value: str | None) -> RolePermissions:
    role = normalize_role(role_value)
    if role == ROLE_SECURITY_ADMIN:
        return RolePermissions(
            can_access_admin=True,
            can_manage_users=True,
            can_view_audit_logs=True,
            can_change_system_config=True,
            can_access_security_dashboard=True,
        )
    if role == ROLE_AUDITOR:
        return RolePermissions(
            can_access_admin=False,
            can_manage_users=False,
            can_view_audit_logs=True,
            can_change_system_config=False,
            can_access_security_dashboard=False,
        )
    if role == ROLE_ORG_ADMIN:
        return RolePermissions(
            can_access_admin=True,
            can_manage_users=True,
            can_view_audit_logs=True,
            can_change_system_config=True,
            can_access_security_dashboard=False,
        )
    return RolePermissions(
        can_access_admin=False,
        can_manage_users=False,
        can_view_audit_logs=False,
        can_change_system_config=False,
        can_access_security_dashboard=False,
    )


def has_any_role(role_value: str | None, *allowed_roles: str) -> bool:
    normalized = normalize_role(role_value)
    return normalized in {normalize_role(role) for role in allowed_roles}
