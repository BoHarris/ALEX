"""
Demonstration: Automatic Task Generation from Test Failures

This test file exists to verify the core utility functions that support the
application and to ensure they behave as expected during CI runs.

For real product validation, this file is intended to exercise small, deterministic
behaviors (e.g., role normalization and key hashing) without requiring an external
service or database access.
"""

from utils.api_key_auth import generate_api_key_secret, hash_api_key
from utils.rbac import get_role_permissions, has_any_role, normalize_role


def test_normalize_role_known_values():
    """Ensure role normalization maps known aliases to canonical values."""
    assert normalize_role("admin") == "organization_admin"
    assert normalize_role("Security_Admin") == "security_admin"
    assert normalize_role("Member") == "user"
    assert normalize_role(None) == "user"


def test_get_role_permissions_security_admin():
    """Security admins should have all elevated permissions."""
    perms = get_role_permissions("security_admin")
    assert perms.can_access_admin
    assert perms.can_manage_users
    assert perms.can_view_audit_logs
    assert perms.can_change_system_config
    assert perms.can_access_security_dashboard


def test_has_any_role_matches_aliases():
    """The helper should treat role aliases as equivalent when checking membership."""
    assert has_any_role("admin", "organization_admin")
    assert has_any_role("member", "user")
    assert not has_any_role("auditor", "security_admin", "organization_admin")


def test_api_key_hashing_is_stable_and_deterministic():
    """Hashing an API key should be deterministic and stable across calls."""
    raw = "test-api-key"
    first = hash_api_key(raw)
    second = hash_api_key(raw)
    assert first == second
    assert len(first) == 64  # sha256 hex digest length


def test_generate_api_key_secret_format():
    """Generated secrets should use the expected prefix and be URL-safe."""
    secret = generate_api_key_secret()
    assert secret.startswith("alex_")
    # Ensure it is URL-safe (no spaces, should be safe for headers/URLs)
    assert " " not in secret
