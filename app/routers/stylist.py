"""
routers/stylist.py — Staff Management APIs
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app import crud, schemas
from app.auth import require_admin_api
from app.database import SessionLocal

router = APIRouter()




def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Public ────────────────────────────────────────────────────────────────────

@router.get("/api/stylists")
def list_stylists(db: Session = Depends(get_db)):
    """Return all active stylists (public — used by booking form and public site)."""
    stylists = crud.get_stylists(db, active_only=True)
    return [
        {
            "id": s.id,
            "full_name": s.full_name,
            "role": s.role,
            "experience_years": s.experience_years,
            "specialization": s.specialization,
            "bio": s.bio,
        }
        for s in stylists
    ]


@router.get("/api/stylists/{stylist_id}/availability", response_model=List[schemas.StylistAvailabilityResponse])
def get_availability(stylist_id: int, db: Session = Depends(get_db)):
    stylist = crud.get_stylist(db, stylist_id)
    if not stylist:
        raise HTTPException(status_code=404, detail="Stylist not found")
    return crud.get_stylist_availability(db, stylist_id)


# ── Admin Only ────────────────────────────────────────────────────────────────

@router.get("/api/stylists/all")
def list_all_stylists(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    """Admin: return all stylists including inactive ones."""
    stylists = crud.get_stylists(db, active_only=False)
    result = []
    for s in stylists:
        stats = crud.get_stylist_stats(db, s.id)
        result.append({
            "id": s.id,
            "full_name": s.full_name,
            "role": s.role,
            "phone": s.phone,
            "email": s.email,
            "experience_years": s.experience_years,
            "specialization": s.specialization,
            "bio": s.bio,
            "is_active": s.is_active,
            **stats,
        })
    return result


@router.post("/api/stylists", response_model=schemas.StylistResponse)
def create_stylist(
    data: schemas.StylistCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    return crud.create_stylist(db, data)


@router.put("/api/stylists/{stylist_id}", response_model=schemas.StylistResponse)
def update_stylist(
    stylist_id: int,
    data: schemas.StylistUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    updated = crud.update_stylist(db, stylist_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Stylist not found")
    return updated


@router.delete("/api/stylists/{stylist_id}")
def delete_stylist(
    stylist_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    stylist = crud.deactivate_stylist(db, stylist_id)
    if not stylist:
        raise HTTPException(status_code=404, detail="Stylist not found")
    return {"message": f"Stylist '{stylist.full_name}' deactivated successfully"}


@router.get("/api/stylists/{stylist_id}/stats")
def stylist_stats(
    stylist_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    stylist = crud.get_stylist(db, stylist_id)
    if not stylist:
        raise HTTPException(status_code=404, detail="Stylist not found")
    return crud.get_stylist_stats(db, stylist_id)


@router.put("/api/stylists/{stylist_id}/availability", response_model=List[schemas.StylistAvailabilityResponse])
def set_availability(
    stylist_id: int,
    entries: list[schemas.StylistAvailabilityCreate],
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    stylist = crud.get_stylist(db, stylist_id)
    if not stylist:
        raise HTTPException(status_code=404, detail="Stylist not found")
    return crud.set_stylist_availability(db, stylist_id, entries)


@router.patch("/api/bookings/{booking_id}/assign-stylist", response_model=schemas.BookingResponse)
def assign_stylist(
    booking_id: int,
    data: schemas.BookingAssignStylist,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    booking = crud.assign_booking_stylist(db, booking_id, data.stylist_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking
