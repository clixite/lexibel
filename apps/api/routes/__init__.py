"""API routes package.

This package contains all FastAPI routers for the LexiBel API.
"""

from apps.api.routes.sentinel import router as sentinel_router

__all__ = ["sentinel_router"]
