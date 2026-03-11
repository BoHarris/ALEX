from __future__ import annotations


PLAN_CONFIG = {
    "free": {
        "scan_limit_per_day": 1,
        "max_file_size_mb": 5,
        "retention_days": 30,
        "admin_analytics": False,
        "audit_visibility": False,
        "company_settings": False,
        "advanced_reporting": False,
    },
    "pro": {
        "scan_limit_per_day": 100,
        "max_file_size_mb": 10,
        "retention_days": 180,
        "admin_analytics": True,
        "audit_visibility": True,
        "company_settings": True,
        "advanced_reporting": True,
    },
    "business": {
        "scan_limit_per_day": 500,
        "max_file_size_mb": 25,
        "retention_days": 365,
        "admin_analytics": True,
        "audit_visibility": True,
        "company_settings": True,
        "advanced_reporting": True,
    },
}


def normalize_tier(tier: str | None) -> str:
    normalized = (tier or "free").strip().lower()
    return normalized if normalized in PLAN_CONFIG else "free"


def get_plan_features(tier: str | None) -> dict:
    normalized = normalize_tier(tier)
    return {"tier": normalized, **PLAN_CONFIG[normalized]}
