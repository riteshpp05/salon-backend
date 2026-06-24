from typing import List

from fastapi import APIRouter, Depends, HTTPException
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


# ── Public: Read Services ─────────────────────────────────────────────────────

@router.get("/api/services", response_model=List[schemas.ServiceResponse])
def all_services(db: Session = Depends(get_db)):
    return crud.get_services(db)

@router.get("/services", response_model=List[schemas.ServiceResponse])
def all_services_old_url(db: Session = Depends(get_db)):
    return all_services(db)


# ── Admin Only: Create / Update / Delete Service ──────────────────────────────

@router.post("/api/services", response_model=schemas.ServiceResponse)
def add_service(
    service: schemas.ServiceCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    return crud.create_service(db, service)

@router.post("/services", response_model=schemas.ServiceResponse)
def add_service_old_url(
    service: schemas.ServiceCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    return add_service(service, db)

@router.put("/api/services/{service_id}", response_model=schemas.ServiceResponse)
def edit_service(
    service_id: int,
    service: schemas.ServiceUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    updated_service = crud.update_service(db, service_id, service)
    if not updated_service:
        raise HTTPException(status_code=404, detail="Service not found")
    return updated_service

@router.delete("/api/services/{service_id}")
def remove_service(
    service_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    deleted_service = crud.delete_service(db, service_id)
    if not deleted_service:
        raise HTTPException(status_code=404, detail="Service not found")
    return {"message": "Service deleted"}

@router.delete("/services/{service_id}")
def remove_service_old_url(
    service_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    return remove_service(service_id, db)


# ── Public: Read Time Slots ───────────────────────────────────────────────────

@router.get("/api/time-slots", response_model=List[schemas.TimeSlotResponse])
def all_time_slots(db: Session = Depends(get_db)):
    return crud.get_time_slots(db)

@router.get("/api/slot-cards")
def slot_cards(db: Session = Depends(get_db)):
    return crud.get_slot_cards(db)

@router.get("/api/slot-cards/{target_date}")
def slot_cards_for_date(target_date: str, db: Session = Depends(get_db)):
    return crud.get_slot_cards(db, target_date=target_date)


# ── Admin Only: Create / Update / Delete Time Slots ──────────────────────────

@router.post("/api/time-slots", response_model=schemas.TimeSlotResponse)
def add_time_slot(
    time_slot: schemas.TimeSlotCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    try:
        return crud.create_time_slot(db, time_slot)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

@router.put("/api/time-slots/{time_slot_id}", response_model=schemas.TimeSlotResponse)
def edit_time_slot(
    time_slot_id: int,
    time_slot: schemas.TimeSlotUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    updated = crud.update_time_slot(db, time_slot_id, time_slot)
    if not updated:
        raise HTTPException(status_code=404, detail="Time slot not found")
    return updated

@router.delete("/api/time-slots/{time_slot_id}")
def remove_time_slot(
    time_slot_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    deleted = crud.delete_time_slot(db, time_slot_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Time slot not found")
    return {"message": "Time slot deleted"}


# ── Admin Only: Dashboard Stats ───────────────────────────────────────────────

@router.get("/api/dashboard-stats")
def dashboard_stats(
    db: Session = Depends(get_db),
):
    stats = crud.get_dashboard_stats(db)
    popular_service = stats.get("popular_service")
    return {
        **stats,
        "popular_service": popular_service[0] if popular_service else "None"
    }
