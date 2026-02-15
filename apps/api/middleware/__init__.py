"""LexiBel API middleware stack.

Registration order (outermost → innermost):
    CORS → RateLimit (stub) → Auth (stub) → Tenant → Audit
RBAC is enforced via route-level dependency, not middleware.
"""
