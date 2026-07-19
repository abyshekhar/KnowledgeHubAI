from __future__ import annotations

ALLOWED_LEVELS_BY_ROLE: dict[str, list[str]] = {
    "admin": ["user", "knowledge_manager", "manager", "admin"],
    "knowledge_manager": ["user", "knowledge_manager", "manager"],
    "user": ["user"],
}


def allowed_access_levels(role_name: str) -> list[str]:
    return ALLOWED_LEVELS_BY_ROLE.get(role_name, ["user"])
