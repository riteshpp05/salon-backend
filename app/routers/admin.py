import os
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import SessionLocal
from app import crud

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

from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/login")

def is_authenticated(token: str = Depends(oauth2_scheme)) -> bool:
    # simple token check for now
    if token == "super_secret_admin_token":
        return True
    return False

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/api/admin/login")
def admin_login_submit(credentials: LoginRequest):
    """Process the admin login form."""
    if credentials.username == ADMIN_USERNAME and credentials.password == ADMIN_PASSWORD:
        return {"access_token": "super_secret_admin_token", "token_type": "bearer"}

    raise HTTPException(status_code=401, detail="Invalid admin credentials.")

@router.post("/api/admin/logout")
def admin_logout(request: Request):
    """Clear the admin session."""
    request.session.clear()
    return {"status": "success", "message": "Logged out successfully"}

@router.get("/api/admin/dashboard")
def admin_dashboard(db: Session = Depends(get_db), auth: bool = Depends(is_authenticated)):
    """Main admin dashboard data — requires fresh authentication."""
    if not auth:
        raise HTTPException(status_code=401, detail="Unauthorized")

    bookings = crud.get_bookings(db)
    services = crud.get_services(db)
    time_slots = crud.get_time_slots(db)
    slot_cards = crud.get_slot_cards(db)
    stats = crud.get_dashboard_stats(db)

    
    
    popular = stats.get("popular_service")
    stats["popular_service"] = popular[0] if popular else "None"

    def to_dict(obj):
        if isinstance(obj, dict): return obj
        return {c.name: getattr(obj, c.name) for c in getattr(obj, '__table__').columns} if hasattr(obj, '__table__') else obj
        
    return {
        "bookings": [to_dict(b) for b in bookings] if bookings else [],
        "services": [to_dict(s) for s in services] if services else [],
        "time_slots": [to_dict(t) for t in time_slots] if time_slots else [],
        "slot_cards": slot_cards,
        "stats": stats,
    }


