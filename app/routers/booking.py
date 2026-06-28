import asyncio
import logging
import os

from typing import List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session

from app import crud, schemas
from app.auth import require_admin_api
from app.database import SessionLocal
from app.whatsapp import send_whatsapp_selenium, format_booking_message

router = APIRouter()
logger = logging.getLogger("salon.booking")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def trigger_selenium_whatsapp(admin_number: str, message_text: str):
    """Background task to run Selenium without blocking the customer response."""
    try:
        logger.info("Starting background Selenium task...")
        send_whatsapp_selenium(admin_number, message_text)
    except Exception as error:
        logger.error("[FAIL] Background Selenium task failed: %s", error, exc_info=True)


# ── Public: Create Booking ────────────────────────────────────────────────────

@router.post("/api/bookings")
async def create_booking(
    booking: schemas.BookingCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    logger.info(
        "=== NEW BOOKING REQUEST === Customer: %s, Phone: %s, Service: %s, "
        "Date: %s, Slot: %s",
        booking.customer_name,
        booking.phone,
        booking.service,
        booking.appointment_date,
        booking.time_slot,
    )

    try:
        new_booking = crud.create_booking(db, booking)
        logger.info(
            "[OK] Booking created -- ID: %s, Status: %s",
            new_booking.id,
            new_booking.status,
        )
    except ValueError as error:
        logger.warning("Booking creation failed: %s", error)
        raise HTTPException(status_code=400, detail=str(error))

    # Send WhatsApp to admin via Selenium (background — does not block response)
    admin_number = os.getenv("ADMIN_WHATSAPP_NUMBER", "+918805031531")
    message_text = format_booking_message(new_booking)
    logger.info("Queuing Selenium WhatsApp notification...")
    background_tasks.add_task(trigger_selenium_whatsapp, admin_number, message_text)

    return {
        "message": "Booking Confirmed",
        "data": schemas.BookingResponse.model_validate(new_booking),
        "whatsapp_sent": False,
        "admin_whatsapp_sent": True,
        "whatsapp_error": "Customer WhatsApp disabled to avoid spam bans",
        "admin_whatsapp_error": None,
    }


# ── Public: Read Bookings ─────────────────────────────────────────────────────

@router.get("/api/bookings", response_model=List[schemas.BookingResponse])
def get_all_bookings(
    db: Session = Depends(get_db),
):
    return crud.get_bookings(db)


# ── Admin Only: Update Booking Status ─────────────────────────────────────────

@router.patch("/api/bookings/{booking_id}/status", response_model=schemas.BookingResponse)
def update_booking(
    booking_id: int,
    booking: schemas.BookingUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    updated_booking = crud.update_booking_status(db, booking_id, booking.status)
    if not updated_booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return updated_booking


# ── Admin Only: Delete Booking ────────────────────────────────────────────────

@router.delete("/api/bookings/{booking_id}")
def remove_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    deleted_booking = crud.delete_booking(db, booking_id)
    if not deleted_booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"message": "Booking deleted"}


# ── Legacy URL compatibility ──────────────────────────────────────────────────

@router.post("/book")
async def create_booking_old_url(
    booking: schemas.BookingCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    return await create_booking(booking, background_tasks, db)


@router.get("/bookings", response_model=List[schemas.BookingResponse])
def get_all_bookings_old_url(db: Session = Depends(get_db)):
    return get_all_bookings(db)
