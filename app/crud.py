import os
from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas

# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────

ACTIVE_STATUSES = ["Pending", "Confirmed"]
REVENUE_STATUSES = ["Confirmed", "Completed"]

DEFAULT_SERVICES = [
    {"name": "Signature Haircut", "price": "900", "duration": "45 min"},
    {"name": "Royal Beard Ritual", "price": "650", "duration": "30 min"},
    {"name": "Gold Facial Therapy", "price": "1800", "duration": "60 min"},
    {"name": "Luxury Hair Spa", "price": "2200", "duration": "75 min"},
    {"name": "Bridal Makeup", "price": "6500", "duration": "120 min"},
]

DEFAULT_TIME_SLOTS = [
    "10:00 AM", "11:00 AM", "12:00 PM",
    "02:00 PM", "03:00 PM", "04:00 PM",
]

# ──────────────────────────────────────────────────────────────────────────────
# SEED
# ──────────────────────────────────────────────────────────────────────────────

def seed_default_data(db: Session):
    existing_service_names = {s.name for s in db.query(models.Service).all()}
    existing_slot_values = {t.slot for t in db.query(models.TimeSlot).all()}

    for service in DEFAULT_SERVICES:
        if service["name"] not in existing_service_names:
            db.add(models.Service(**service))

    for slot in DEFAULT_TIME_SLOTS:
        if slot not in existing_slot_values:
            db.add(models.TimeSlot(slot=slot, slot_time=slot, is_available="Yes"))

    db.commit()


def sync_slot_booking_state(db: Session, target_date: str = None):
    if target_date is None:
        target_date = date.today().isoformat()

    slots = db.query(models.TimeSlot).all()
    for slot in slots:
        active_booking = (
            db.query(models.Booking)
            .filter(models.Booking.time_slot == (slot.slot_time or slot.slot))
            .filter(models.Booking.appointment_date == target_date)
            .filter(models.Booking.status.in_(ACTIVE_STATUSES))
            .order_by(models.Booking.id.desc())
            .first()
        )
        slot.is_available = "No" if active_booking else "Yes"
        slot.booking_id = active_booking.id if active_booking else None

    db.commit()


# ──────────────────────────────────────────────────────────────────────────────
# SERVICES
# ──────────────────────────────────────────────────────────────────────────────

def create_service(db: Session, service: schemas.ServiceCreate):
    db_service = models.Service(**service.dict())
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service


def get_services(db: Session):
    return db.query(models.Service).all()


def update_service(db: Session, service_id: int, service_data: schemas.ServiceUpdate):
    service = db.query(models.Service).filter(models.Service.id == service_id).first()
    if service:
        service.name = service_data.name
        service.price = service_data.price
        service.duration = service_data.duration
        db.commit()
        db.refresh(service)
    return service


def delete_service(db: Session, service_id: int):
    service = db.query(models.Service).filter(models.Service.id == service_id).first()
    if service:
        db.delete(service)
        db.commit()
    return service


# ──────────────────────────────────────────────────────────────────────────────
# TIME SLOTS
# ──────────────────────────────────────────────────────────────────────────────

def create_time_slot(db: Session, time_slot: schemas.TimeSlotCreate):
    slot_value = time_slot.slot_time or time_slot.slot
    if not slot_value:
        raise ValueError("Slot time is required")
    db_time_slot = models.TimeSlot(
        slot=slot_value, slot_time=slot_value, is_available=time_slot.is_available
    )
    db.add(db_time_slot)
    db.commit()
    db.refresh(db_time_slot)
    return db_time_slot


def get_time_slots(db: Session):
    return db.query(models.TimeSlot).order_by(models.TimeSlot.id).all()


def update_time_slot(db: Session, time_slot_id: int, time_slot_data: schemas.TimeSlotUpdate):
    time_slot = db.query(models.TimeSlot).filter(models.TimeSlot.id == time_slot_id).first()
    if time_slot:
        slot_value = time_slot_data.slot_time or time_slot_data.slot
        if slot_value:
            time_slot.slot = slot_value
            time_slot.slot_time = slot_value
        time_slot.is_available = time_slot_data.is_available
        if time_slot.is_available == "Yes":
            time_slot.booking_id = None
        db.commit()
        db.refresh(time_slot)
    return time_slot


def delete_time_slot(db: Session, time_slot_id: int):
    time_slot = db.query(models.TimeSlot).filter(models.TimeSlot.id == time_slot_id).first()
    if time_slot:
        db.delete(time_slot)
        db.commit()
    return time_slot


# ──────────────────────────────────────────────────────────────────────────────
# STYLISTS
# ──────────────────────────────────────────────────────────────────────────────

def create_stylist(db: Session, data: schemas.StylistCreate) -> models.Stylist:
    stylist = models.Stylist(**data.dict())
    db.add(stylist)
    db.commit()
    db.refresh(stylist)
    return stylist


def get_stylists(db: Session, active_only: bool = True):
    q = db.query(models.Stylist)
    if active_only:
        q = q.filter(models.Stylist.is_active == True)
    return q.order_by(models.Stylist.id).all()


def get_stylist(db: Session, stylist_id: int) -> Optional[models.Stylist]:
    return db.query(models.Stylist).filter(models.Stylist.id == stylist_id).first()


def update_stylist(db: Session, stylist_id: int, data: schemas.StylistUpdate) -> Optional[models.Stylist]:
    stylist = get_stylist(db, stylist_id)
    if stylist:
        for field, value in data.dict().items():
            setattr(stylist, field, value)
        db.commit()
        db.refresh(stylist)
    return stylist


def deactivate_stylist(db: Session, stylist_id: int) -> Optional[models.Stylist]:
    stylist = get_stylist(db, stylist_id)
    if stylist:
        stylist.is_active = False
        db.commit()
        db.refresh(stylist)
    return stylist


def delete_stylist(db: Session, stylist_id: int) -> Optional[models.Stylist]:
    stylist = get_stylist(db, stylist_id)
    if stylist:
        db.delete(stylist)
        db.commit()
    return stylist


# ── Stylist Availability ──────────────────────────────────────────────────────

def get_stylist_availability(db: Session, stylist_id: int):
    return (
        db.query(models.StylistAvailability)
        .filter(models.StylistAvailability.stylist_id == stylist_id)
        .order_by(models.StylistAvailability.day_of_week)
        .all()
    )


def set_stylist_availability(db: Session, stylist_id: int, entries: list[schemas.StylistAvailabilityCreate]):
    # Replace all existing availability for this stylist
    db.query(models.StylistAvailability).filter(
        models.StylistAvailability.stylist_id == stylist_id
    ).delete()

    for entry in entries:
        row = models.StylistAvailability(stylist_id=stylist_id, **entry.dict())
        db.add(row)

    db.commit()
    return get_stylist_availability(db, stylist_id)


# ── Stylist Analytics ─────────────────────────────────────────────────────────

def get_stylist_stats(db: Session, stylist_id: int) -> dict:
    all_bookings = (
        db.query(models.Booking)
        .filter(models.Booking.stylist_id == stylist_id)
        .all()
    )
    today = date.today().isoformat()
    revenue_bookings = [b for b in all_bookings if b.status in REVENUE_STATUSES]
    total_revenue = sum(
        int(b.price or 0) for b in revenue_bookings if (b.price or "0").isdigit()
    )
    upcoming = [
        b for b in all_bookings
        if b.appointment_date >= today and b.status in ACTIVE_STATUSES
    ]
    popular = (
        db.query(models.Booking.service, func.count(models.Booking.id))
        .filter(models.Booking.stylist_id == stylist_id)
        .filter(models.Booking.status.in_(REVENUE_STATUSES))
        .group_by(models.Booking.service)
        .order_by(func.count(models.Booking.id).desc())
        .first()
    )
    return {
        "total_bookings": len(all_bookings),
        "completed_bookings": len([b for b in all_bookings if b.status == "Completed"]),
        "total_revenue": total_revenue,
        "popular_service": popular[0] if popular else "N/A",
        "upcoming_count": len(upcoming),
    }


# ──────────────────────────────────────────────────────────────────────────────
# BOOKINGS
# ──────────────────────────────────────────────────────────────────────────────

def create_booking(db: Session, booking: schemas.BookingCreate) -> models.Booking:
    booking_data = booking.dict()
    appointment_date = booking.appointment_date or date.today().isoformat()
    booking_data["appointment_date"] = appointment_date
    booking_data["age"] = booking.age or "Not provided"
    booking_data["whatsapp_number"] = booking.phone

    # Verify service exists
    service = db.query(models.Service).filter(models.Service.name == booking.service).first()
    if not service:
        raise ValueError(
            f"Service '{booking.service}' was not found. "
            "Please select a valid service from the list."
        )

    # Verify time slot exists
    time_slot = db.query(models.TimeSlot).filter(
        models.TimeSlot.slot_time == booking.time_slot
    ).first()
    if not time_slot:
        raise ValueError(
            f"Time slot '{booking.time_slot}' does not exist. "
            "Please select a valid time slot."
        )

    # Verify stylist exists (if specified)
    if booking.stylist_id is not None:
        stylist = get_stylist(db, booking.stylist_id)
        if not stylist or not stylist.is_active:
            raise ValueError(
                "The selected stylist is not available. "
                "Please choose another stylist."
            )
        # Per-stylist conflict check
        stylist_conflict = (
            db.query(models.Booking)
            .filter(models.Booking.stylist_id == booking.stylist_id)
            .filter(models.Booking.time_slot == booking.time_slot)
            .filter(models.Booking.appointment_date == appointment_date)
            .filter(models.Booking.status.in_(ACTIVE_STATUSES))
            .first()
        )
        if stylist_conflict:
            raise ValueError(
                "This stylist is already booked for that time slot. "
                "Please choose another stylist or a different time."
            )

    # Global slot conflict check
    existing_booking = (
        db.query(models.Booking)
        .filter(models.Booking.time_slot == booking.time_slot)
        .filter(models.Booking.appointment_date == appointment_date)
        .filter(models.Booking.status.in_(ACTIVE_STATUSES))
        .first()
    )
    if existing_booking:
        raise ValueError(
            "This slot has just been booked. "
            "Please select another time slot."
        )

    db_booking = models.Booking(
        **booking_data,
        price=service.price,
        service_duration=service.duration,
        status="Confirmed",
    )
    db.add(db_booking)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(
            "This slot was just booked by another customer. "
            "Please select another time slot."
        )

    db.refresh(db_booking)
    return db_booking


def get_bookings(db: Session):
    return db.query(models.Booking).order_by(models.Booking.id.desc()).all()


def update_booking_status(db: Session, booking_id: int, status: str):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if booking:
        booking.status = status
        db.commit()
        db.refresh(booking)
    return booking


def assign_booking_stylist(db: Session, booking_id: int, stylist_id: Optional[int]):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if booking:
        booking.stylist_id = stylist_id
        db.commit()
        db.refresh(booking)
    return booking


def delete_booking(db: Session, booking_id: int):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if booking:
        db.delete(booking)
        db.commit()
    return booking


def get_slot_cards(db: Session, target_date: str = None):
    if target_date is None:
        target_date = date.today().isoformat()

    slots = get_time_slots(db)
    cards = []
    for slot in slots:
        slot_time_value = slot.slot_time or slot.slot
        booking = (
            db.query(models.Booking)
            .filter(models.Booking.time_slot == slot_time_value)
            .filter(models.Booking.appointment_date == target_date)
            .filter(models.Booking.status.in_(ACTIVE_STATUSES))
            .first()
        )
        cards.append({
            "id": slot.id,
            "slot_time": slot_time_value,
            "is_available": "No" if booking else "Yes",
            "booking_id": booking.id if booking else None,
            "state": "booked" if booking else "available",
            "customer_name": booking.customer_name if booking else "",
            "service": booking.service if booking else "",
            "status": booking.status if booking else "",
            "stylist_id": booking.stylist_id if booking else None,
        })
    return cards


def get_dashboard_stats(db: Session):
    all_bookings = get_bookings(db)
    slots = get_time_slots(db)
    today_value = date.today().isoformat()

    revenue_bookings = [b for b in all_bookings if b.status in REVENUE_STATUSES]
    total_revenue = sum(
        int(b.price or 0) for b in revenue_bookings if (b.price or "0").isdigit()
    )
    today_revenue = sum(
        int(b.price or 0)
        for b in revenue_bookings
        if b.appointment_date == today_value and (b.price or "0").isdigit()
    )
    status_counts = {
        s: db.query(models.Booking).filter(models.Booking.status == s).count()
        for s in ["Pending", "Confirmed", "Completed", "Cancelled"]
    }
    return {
        "total_bookings": len(all_bookings),
        "today_bookings": len([b for b in all_bookings if b.appointment_date == today_value]),
        "available_slots": len([s for s in slots if s.is_available == "Yes"]),
        "booked_slots": len([s for s in slots if s.is_available != "Yes"]),
        "total_revenue": total_revenue,
        "today_revenue": today_revenue,
        "active_bookings": len([b for b in all_bookings if b.status in ACTIVE_STATUSES]),
        "status_counts": status_counts,
        "popular_service": (
            db.query(models.Booking.service, func.count(models.Booking.id))
            .filter(models.Booking.status.in_(REVENUE_STATUSES))
            .group_by(models.Booking.service)
            .order_by(func.count(models.Booking.id).desc())
            .first()
        ),
        "total_stylists": db.query(models.Stylist).filter(models.Stylist.is_active == True).count(),
        "total_gallery": db.query(models.GalleryItem).filter(models.GalleryItem.is_published == True).count(),
        "total_customers": db.query(models.Customer).count(),
    }


# ──────────────────────────────────────────────────────────────────────────────
# GALLERY
# ──────────────────────────────────────────────────────────────────────────────

def create_gallery_item(db: Session, data: schemas.GalleryItemCreate) -> models.GalleryItem:
    item = models.GalleryItem(**data.dict())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_gallery_items(db: Session, published_only: bool = True, service_type: str = None):
    q = db.query(models.GalleryItem)
    if published_only:
        q = q.filter(models.GalleryItem.is_published == True)
    if service_type and service_type.lower() != "all":
        q = q.filter(models.GalleryItem.service_type == service_type)
    return q.order_by(models.GalleryItem.display_order, models.GalleryItem.id).all()


def get_gallery_item(db: Session, item_id: int) -> Optional[models.GalleryItem]:
    return db.query(models.GalleryItem).filter(models.GalleryItem.id == item_id).first()


def update_gallery_item(db: Session, item_id: int, data: schemas.GalleryItemUpdate) -> Optional[models.GalleryItem]:
    item = get_gallery_item(db, item_id)
    if item:
        for field, value in data.dict().items():
            setattr(item, field, value)
        db.commit()
        db.refresh(item)
    return item


def toggle_gallery_publish(db: Session, item_id: int) -> Optional[models.GalleryItem]:
    item = get_gallery_item(db, item_id)
    if item:
        item.is_published = not item.is_published
        db.commit()
        db.refresh(item)
    return item


def reorder_gallery(db: Session, order_map: dict[int, int]):
    """order_map = {item_id: new_display_order}"""
    for item_id, new_order in order_map.items():
        item = get_gallery_item(db, item_id)
        if item:
            item.display_order = new_order
    db.commit()


def delete_gallery_item(db: Session, item_id: int) -> Optional[models.GalleryItem]:
    item = get_gallery_item(db, item_id)
    if item:
        db.delete(item)
        db.commit()
    return item


# ──────────────────────────────────────────────────────────────────────────────
# CUSTOMERS
# ──────────────────────────────────────────────────────────────────────────────

def get_or_create_customer(db: Session, data: schemas.CustomerCreate) -> tuple[models.Customer, bool]:
    """Return (customer, created). If phone exists, return existing record."""
    # Normalize phone for lookup
    phone = data.phone.strip()
    existing = db.query(models.Customer).filter(models.Customer.phone == phone).first()
    if existing:
        return existing, False

    customer = models.Customer(full_name=data.full_name, phone=phone)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer, True


def get_customer_by_phone(db: Session, phone: str) -> Optional[models.Customer]:
    return db.query(models.Customer).filter(models.Customer.phone == phone).first()


def get_customer(db: Session, customer_id: int) -> Optional[models.Customer]:
    return db.query(models.Customer).filter(models.Customer.id == customer_id).first()


def update_customer(db: Session, customer_id: int, data: schemas.CustomerUpdate) -> Optional[models.Customer]:
    customer = get_customer(db, customer_id)
    if customer:
        if data.full_name:
            customer.full_name = data.full_name
        customer.preferred_stylist_id = data.preferred_stylist_id
        db.commit()
        db.refresh(customer)
    return customer


def get_customer_bookings(db: Session, customer_id: int) -> dict:
    customer = get_customer(db, customer_id)
    if not customer:
        return {"upcoming": [], "past": []}

    today = date.today().isoformat()
    bookings = (
        db.query(models.Booking)
        .filter(models.Booking.phone == customer.phone)
        .order_by(models.Booking.appointment_date.desc())
        .all()
    )
    upcoming = [
        b for b in bookings
        if b.appointment_date >= today and b.status in ACTIVE_STATUSES
    ]
    past = [b for b in bookings if b not in upcoming]
    return {"upcoming": upcoming, "past": past}


def cancel_booking_by_customer(db: Session, booking_id: int, customer_phone: str) -> Optional[models.Booking]:
    """Customer can only cancel their own bookings."""
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        return None
    if booking.phone != customer_phone:
        raise PermissionError("You can only cancel your own bookings.")
    if booking.status not in ACTIVE_STATUSES:
        raise ValueError(f"Booking cannot be cancelled (current status: {booking.status}).")
    booking.status = "Cancelled"
    db.commit()
    db.refresh(booking)
    return booking


def award_loyalty_points(db: Session, customer_phone: str, booking_price: str):
    """Award 1 loyalty point per ₹1 spent (Confirmed/Completed bookings only)."""
    customer = get_customer_by_phone(db, customer_phone)
    if customer:
        try:
            points = int(booking_price or 0)
            customer.loyalty_points += points
            db.commit()
        except (ValueError, TypeError):
            pass


def get_bookings_by_phone(db: Session, phone: str):
    return db.query(models.Booking).filter(models.Booking.phone == phone).order_by(models.Booking.appointment_date.desc()).all()
