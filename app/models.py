from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey,
    Integer, String, Text
)
from app.database import Base


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(String, nullable=False)
    duration = Column(String, nullable=False)


class TimeSlot(Base):
    __tablename__ = "time_slots"

    id = Column(Integer, primary_key=True, index=True)
    slot = Column(String, nullable=False, unique=True)
    slot_time = Column(String, nullable=False, default="")
    is_available = Column(String, default="Yes")
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)


class Stylist(Base):
    __tablename__ = "stylists"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    role = Column(String(100), nullable=False, default="Stylist")
    phone = Column(String(20), nullable=True, default="")
    email = Column(String(200), nullable=True, default="")
    profile_image = Column(String(500), nullable=True, default="")
    experience_years = Column(Integer, nullable=False, default=0)
    specialization = Column(Text, nullable=True, default="")
    bio = Column(Text, nullable=True, default="")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class StylistAvailability(Base):
    __tablename__ = "stylist_availability"

    id = Column(Integer, primary_key=True, index=True)
    stylist_id = Column(Integer, ForeignKey("stylists.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)   # 0=Mon … 6=Sun
    start_time = Column(String(10), nullable=False, default="10:00 AM")
    end_time = Column(String(10), nullable=False, default="07:00 PM")
    is_working = Column(Boolean, nullable=False, default=True)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    whatsapp_number = Column(String, nullable=True, default="")
    age = Column(String, nullable=False, default="")
    service = Column(String, nullable=False)
    price = Column(String, nullable=False, default="")
    service_duration = Column(String, nullable=False, default="")
    appointment_date = Column(String, nullable=False, default="")
    time_slot = Column(String, nullable=False)
    status = Column(String, default="Confirmed")
    stylist_id = Column(Integer, ForeignKey("stylists.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GalleryItem(Base):
    __tablename__ = "gallery_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True, default="")
    service_type = Column(String(100), nullable=False, default="General")
    before_image = Column(String(500), nullable=True, default="")
    after_image = Column(String(500), nullable=True, default="")
    display_order = Column(Integer, nullable=False, default=0)
    is_published = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False, unique=True)
    preferred_stylist_id = Column(Integer, ForeignKey("stylists.id"), nullable=True)
    loyalty_points = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
