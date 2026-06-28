"""
app/auth.py
-----------
Shared authentication dependency used by all admin-only API routes.

Supports BOTH:
  1. Bearer token auth (Authorization: Bearer super_secret_admin_token)
  2. Session cookie auth (admin_logged_in = True in session)

This allows the separated frontend (Hostinger) to use token-based auth
while keeping backward compatibility with session-based auth.

Usage:
    from app.auth import require_admin_api

    @router.delete("/api/services/{id}")
    def remove_service(service_id: int, _=Depends(require_admin_api)):
        ...
"""
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
import os

# The valid admin token — must match what admin.py returns on login
VALID_ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "super_secret_admin_token")

# Optional scheme — won't raise 401 automatically if token missing
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/admin/login", auto_error=False)


def require_admin_api(
    request: Request,
    token: str = Depends(oauth2_scheme_optional),
) -> None:
    """
    FastAPI dependency that protects admin-only API endpoints.

    Accepts authentication via:
    - Bearer token in Authorization header (for separated frontend)
    - Session cookie set by SessionMiddleware (for legacy access)

    Raises HTTP 401 if neither is valid.
    """
    # Check bearer token first (preferred for separated architecture)
    if token and token == VALID_ADMIN_TOKEN:
        return

    # Fallback: check session cookie (legacy / monolith mode)
    if request.session.get("admin_logged_in"):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=(
            "Authentication required. "
            "Please provide a valid Authorization: Bearer token."
        ),
        headers={"WWW-Authenticate": "Bearer"},
    )
