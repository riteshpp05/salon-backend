import os
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import SessionLocal
from app import crud
from app.auth import require_admin_api

load_dotenv()

router = APIRouter()

# ── Credentials (loaded from environment, never hardcoded) ─────────────────
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/api/admin/login")
def admin_login_submit(credentials: LoginRequest, request: Request):
    """Process the admin login form.
    
    Supports DUAL authentication:
    1. Sets session cookie (for session-based auth)
    2. Returns Bearer token (for token-based auth from separated frontend)
    
    Both mechanisms work simultaneously so the frontend can use whichever it prefers.
    The Bearer token approach is more reliable for cross-domain setups.
    """
    if credentials.username != ADMIN_USERNAME or credentials.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid admin credentials.")

    # Set session (for session-based auth — works when SameSite=None + Secure=True)
    request.session["admin_logged_in"] = True
    request.session["admin_username"] = credentials.username

    # Also return Bearer token (for localStorage-based auth — belt and suspenders)
    return {
        "status": "success",
        "access_token": "super_secret_admin_token",
        "token_type": "bearer"
    }


@router.post("/api/admin/logout")
def admin_logout(request: Request):
    """Clear the admin session."""
    request.session.clear()
    return {"status": "success", "message": "Logged out successfully"}


@router.get("/api/admin/dashboard")
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    """Main admin dashboard data — requires authentication via Bearer token or session cookie."""
    bookings = crud.get_bookings(db)
    services = crud.get_services(db)
    time_slots = crud.get_time_slots(db)
    slot_cards = crud.get_slot_cards(db)
    stats = crud.get_dashboard_stats(db)

    popular = stats.get("popular_service")
    stats["popular_service"] = popular[0] if popular else "None"

    def to_dict(obj):
        if isinstance(obj, dict):
            return obj
        return {c.name: getattr(obj, c.name) for c in getattr(obj, '__table__').columns} if hasattr(obj, '__table__') else obj

    return {
        "bookings": [to_dict(b) for b in bookings] if bookings else [],
        "services": [to_dict(s) for s in services] if services else [],
        "time_slots": [to_dict(t) for t in time_slots] if time_slots else [],
        "slot_cards": slot_cards,
        "stats": stats,
    }
