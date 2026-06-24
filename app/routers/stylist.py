"""
routers/stylist.py — Staff Management APIs
"""
import os
import uuid

from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.orm import Session

from app import crud, schemas
from app.auth import require_admin_api
from app.database import SessionLocal

router = APIRouter()

STYLIST_IMAGE_DIR = os.path.join("app", "static", "stylists")
os.makedirs(STYLIST_IMAGE_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


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
            "profile_image": (
                f"/static/stylists/{s.profile_image}"
                if s.profile_image and not s.profile_image.startswith("http")
                else s.profile_image or ""
            ),
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
            "profile_image": (
                f"/static/stylists/{s.profile_image}"
                if s.profile_image and not s.profile_image.startswith("http")
                else s.profile_image or ""
            ),
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


@router.post("/api/stylists/{stylist_id}/upload-image")
async def upload_stylist_image(
    stylist_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    stylist = crud.get_stylist(db, stylist_id)
    if not stylist:
        raise HTTPException(status_code=404, detail="Stylist not found")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{ext}'. Allowed: JPG, PNG, WEBP."
        )

    # Compress with Pillow and save as WebP
    try:
        from PIL import Image
        import io
        content = await file.read()
        img = Image.open(io.BytesIO(content)).convert("RGB")
        img.thumbnail((600, 600))
        filename = f"stylist_{stylist_id}_{uuid.uuid4().hex[:8]}.webp"
        save_path = os.path.join(STYLIST_IMAGE_DIR, filename)
        img.save(save_path, "WEBP", quality=85)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image processing failed: {e}")

    # Delete old image if it exists
    if stylist.profile_image:
        old_path = os.path.join(STYLIST_IMAGE_DIR, stylist.profile_image)
        if os.path.exists(old_path):
            os.remove(old_path)

    crud.update_stylist_image(db, stylist_id, filename)
    return {"message": "Image uploaded", "filename": filename, "url": f"/static/stylists/{filename}"}


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
