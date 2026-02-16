"""RBAC middleware — role-based access control via route dependency.

Uses a decorator pattern: @require_role("partner", "admin") on route
functions. The decorator reads request.state.user_role (set by auth/tenant
middleware) and returns 403 if the role is insufficient.

Role hierarchy (highest → lowest):
    super_admin > admin > partner > associate > junior > secretary > accountant
"""

import functools
from collections.abc import Callable, Sequence
from typing import Any

from fastapi import HTTPException, Request, status

from packages.db.models.user import UserRole

# Ordered from most privileged to least.
ROLE_HIERARCHY: list[str] = [
    UserRole.SUPER_ADMIN.value,
    UserRole.ADMIN.value,
    UserRole.PARTNER.value,
    UserRole.ASSOCIATE.value,
    UserRole.JUNIOR.value,
    UserRole.SECRETARY.value,
    UserRole.ACCOUNTANT.value,
]

_ROLE_RANK: dict[str, int] = {role: i for i, role in enumerate(ROLE_HIERARCHY)}


def has_role(user_role: str, required: str) -> bool:
    """Return True if *user_role* is at least as privileged as *required*."""
    user_rank = _ROLE_RANK.get(user_role)
    required_rank = _ROLE_RANK.get(required)
    if user_rank is None or required_rank is None:
        return False
    # Lower rank number = more privileged.
    return user_rank <= required_rank


def check_roles(user_role: str, allowed_roles: Sequence[str]) -> bool:
    """Return True if *user_role* matches any of *allowed_roles* (exact match)."""
    return user_role in allowed_roles


def require_role(*allowed_roles: str) -> Callable:
    """FastAPI route decorator that enforces RBAC.

    Usage::

        @router.get("/admin-only")
        @require_role("admin", "super_admin")
        async def admin_endpoint(request: Request):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request: Request | None = kwargs.get("request")
            if request is None:
                # Try positional args (FastAPI injects Request)
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found in route handler",
                )

            user_role: str | None = getattr(request.state, "user_role", None)
            if user_role is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            if not check_roles(user_role, allowed_roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{user_role}' not in allowed roles: {list(allowed_roles)}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
