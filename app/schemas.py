import re
from datetime import date as date_type
from typing import Optional

from pydantic import BaseModel, field_validator


# ──────────────────────────────────────────────────────────────────────────────
# SERVICE SCHEMAS
# ──────────────────────────────────────────────────────────────────────────────

class ServiceCreate(BaseModel):
    name: str
    price: str
    duration: str


class ServiceUpdate(ServiceCreate):
    pass


class ServiceResponse(ServiceCreate):
    id: int
    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────────────────────────
# TIME SLOT SCHEMAS
# ──────────────────────────────────────────────────────────────────────────────

class TimeSlotCreate(BaseModel):
    slot: str | None = None
    slot_time: str | None = None
    is_available: str = "Yes"

    @field_validator("is_available", mode="before")
    @classmethod
    def validate_is_available(cls, v):
        if isinstance(v, bool):
            return "Yes" if v else "No"
        if isinstance(v, str):
            if v.lower() == "true": return "Yes"
            if v.lower() == "false": return "No"
        return v


class TimeSlotUpdate(TimeSlotCreate):
    pass


class TimeSlotResponse(TimeSlotCreate):
    id: int
    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────────────────────────
# STYLIST SCHEMAS
# ──────────────────────────────────────────────────────────────────────────────

class StylistCreate(BaseModel):
    full_name: str
    role: str = "Stylist"
    phone: str = ""
    email: str = ""
    experience_years: int = 0
    specialization: str = ""
    bio: str = ""

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Stylist name is required.")
        return v


class StylistUpdate(StylistCreate):
    is_active: bool = True


class StylistResponse(BaseModel):
    id: int
    full_name: str
    role: str
    phone: str
    email: str
    experience_years: int
    specialization: str
    bio: str
    is_active: bool
    class Config:
        from_attributes = True


class StylistAvailabilityCreate(BaseModel):
    day_of_week: int          # 0=Mon … 6=Sun
    start_time: str = "10:00 AM"
    end_time: str = "07:00 PM"
    is_working: bool = True


class StylistAvailabilityResponse(StylistAvailabilityCreate):
    id: int
    stylist_id: int
    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────────────────────────
# BOOKING SCHEMAS
# ──────────────────────────────────────────────────────────────────────────────

class BookingCreate(BaseModel):
    customer_name: str
    phone: str
    age: str = ""
    service: str
    appointment_date: str = ""
    time_slot: str
    stylist_id: Optional[int] = None   # None means "any stylist"

    @field_validator("customer_name")
    @classmethod
    def validate_customer_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Customer name is required and cannot be empty.")
        if len(stripped) < 2:
            raise ValueError("Customer name must be at least 2 characters long.")
        if len(stripped) > 100:
            raise ValueError("Customer name is too long (maximum 100 characters).")
        if not re.match(r"^[a-zA-Z\u00C0-\u024F\s.\-']+$", stripped):
            raise ValueError(
                "Customer name contains invalid characters. "
                "Only letters, spaces, dots, hyphens, and apostrophes are allowed."
            )
        return stripped

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-\(\)]+", "", v.strip())
        if not cleaned:
            raise ValueError("Phone number is required.")
        digits_only = cleaned.replace("whatsapp:", "").lstrip("+")
        if not digits_only.isdigit():
            raise ValueError(f"Phone number contains invalid characters: '{v}'.")
        if len(digits_only) < 10:
            raise ValueError(
                f"Phone number too short ({len(digits_only)} digits). "
                "Please include your country code (e.g. +917028111146)."
            )
        if len(digits_only) > 15:
            raise ValueError(f"Phone number too long ({len(digits_only)} digits).")
        return cleaned

    @field_validator("appointment_date")
    @classmethod
    def validate_appointment_date(cls, v: str) -> str:
        if not v:
            return date_type.today().isoformat()
        try:
            parsed = date_type.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Invalid date format: '{v}'. Please use YYYY-MM-DD format.")
        today = date_type.today()
        if parsed < today:
            raise ValueError(
                "Appointments cannot be booked for past dates. "
                "Please select today or a future date."
            )
        from datetime import timedelta
        if parsed > today + timedelta(days=365):
            raise ValueError("Appointments cannot be booked more than 1 year in advance.")
        return v

    @field_validator("service")
    @classmethod
    def validate_service(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Service selection is required.")
        return stripped

    @field_validator("time_slot")
    @classmethod
    def validate_time_slot(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Time slot selection is required.")
        return stripped


class BookingUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"Pending", "Confirmed", "Completed", "Cancelled"}
        if v not in allowed:
            raise ValueError(
                f"Invalid status '{v}'. "
                f"Allowed values: {', '.join(sorted(allowed))}"
            )
        return v


class BookingAssignStylist(BaseModel):
    stylist_id: Optional[int] = None


class BookingResponse(BookingCreate):
    id: int
    price: str
    service_duration: str
    status: str
    stylist_id: Optional[int] = None
    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────────────────────────
# GALLERY SCHEMAS
# ──────────────────────────────────────────────────────────────────────────────

class GalleryItemCreate(BaseModel):
    title: str
    description: str = ""
    service_type: str = "General"
    display_order: int = 0

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Gallery item title is required.")
        return v


class GalleryItemUpdate(GalleryItemCreate):
    pass


class GalleryItemResponse(BaseModel):
    id: int
    title: str
    description: str
    service_type: str
    display_order: int
    is_published: bool
    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────────────────────────
# CUSTOMER SCHEMAS
# ──────────────────────────────────────────────────────────────────────────────

class CustomerLogin(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-\(\)]+", "", v.strip())
        if not cleaned:
            raise ValueError("Phone number is required.")
        digits_only = cleaned.lstrip("+")
        if not digits_only.isdigit():
            raise ValueError("Invalid phone number.")
        if len(digits_only) < 10:
            raise ValueError("Phone number too short.")
        return cleaned


class CustomerCreate(CustomerLogin):
    full_name: str

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) < 2:
            raise ValueError("Please provide your full name (at least 2 characters).")
        return v


class CustomerUpdate(BaseModel):
    full_name: str = ""
    preferred_stylist_id: Optional[int] = None


class CustomerResponse(BaseModel):
    id: int
    full_name: str
    phone: str
    preferred_stylist_id: Optional[int]
    loyalty_points: int
    class Config:
        from_attributes = True
