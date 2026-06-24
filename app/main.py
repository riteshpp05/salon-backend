import logging
import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from sqlalchemy import inspect, text

from app.database import engine, Base
from app.database import SessionLocal
from app import crud
from app.routers import booking, service, admin, stylist, gallery, customer, analytics

# --------------- Load Environment Variables --------------- #
load_dotenv()

# --------------- Logging Setup --------------- #

def setup_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
    for logger_name in ["salon.whatsapp", "salon.booking", "salon"]:
        lg = logging.getLogger(logger_name)
        lg.setLevel(logging.DEBUG)
        if not lg.handlers:
            lg.addHandler(console_handler)
    logging.getLogger("salon").info("[OK] Salon logging initialized")


setup_logging()
logger = logging.getLogger("salon")

# --------------- Database Tables --------------- #

Base.metadata.create_all(bind=engine)


def ensure_booking_columns():
    existing = {c["name"] for c in inspect(engine).get_columns("bookings")}
    migrations = {
        "age": "ALTER TABLE bookings ADD COLUMN age VARCHAR NOT NULL DEFAULT ''",
        "price": "ALTER TABLE bookings ADD COLUMN price VARCHAR NOT NULL DEFAULT ''",
        "appointment_date": "ALTER TABLE bookings ADD COLUMN appointment_date VARCHAR NOT NULL DEFAULT ''",
        "service_duration": "ALTER TABLE bookings ADD COLUMN service_duration VARCHAR NOT NULL DEFAULT ''",
        "created_at": "ALTER TABLE bookings ADD COLUMN created_at DATETIME",
        "updated_at": "ALTER TABLE bookings ADD COLUMN updated_at DATETIME",
        "whatsapp_number": "ALTER TABLE bookings ADD COLUMN whatsapp_number VARCHAR DEFAULT ''",
        "stylist_id": "ALTER TABLE bookings ADD COLUMN stylist_id INTEGER REFERENCES stylists(id)",
        "customer_id": "ALTER TABLE bookings ADD COLUMN customer_id INTEGER REFERENCES customers(id)",
    }
    with engine.begin() as conn:
        for col, stmt in migrations.items():
            if col not in existing:
                logger.info("Adding column '%s' to bookings", col)
                conn.execute(text(stmt))


def ensure_time_slot_columns():
    existing = {c["name"] for c in inspect(engine).get_columns("time_slots")}
    migrations = {
        "slot_time": "ALTER TABLE time_slots ADD COLUMN slot_time VARCHAR NOT NULL DEFAULT ''",
        "booking_id": "ALTER TABLE time_slots ADD COLUMN booking_id INTEGER",
    }
    with engine.begin() as conn:
        for col, stmt in migrations.items():
            if col not in existing:
                logger.info("Adding column '%s' to time_slots", col)
                conn.execute(text(stmt))
        conn.execute(text(
            "UPDATE time_slots SET slot_time = slot WHERE slot_time IS NULL OR slot_time = ''"
        ))


def ensure_unique_booking_constraint():
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_slot_date "
            "ON bookings (time_slot, appointment_date) "
            "WHERE status NOT IN ('Cancelled')"
        ))
    logger.info("[OK] Unique booking constraint ensured")


ensure_booking_columns()
ensure_time_slot_columns()
ensure_unique_booking_constraint()

db = SessionLocal()
try:
    crud.seed_default_data(db)
    crud.sync_slot_booking_state(db)
finally:
    db.close()

# --------------- FastAPI App --------------- #

app = FastAPI(title="THE HAIR ENGINEER API")

_secret_key = os.getenv("SECRET_KEY", "fallback-insecure-key-set-SECRET_KEY-in-env")
if _secret_key == "fallback-insecure-key-set-SECRET_KEY-in-env":
    logger.warning("[SECURITY] SECRET_KEY not set in environment.")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:5500", "https://thehairengineer.in"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=_secret_key,
    session_cookie="salon_session",
    max_age=None,    # Session-only cookie, clears when browser closes
    https_only=False,
    same_site="lax",
)

# Routers
app.include_router(booking.router)
app.include_router(service.router)
app.include_router(admin.router)
app.include_router(stylist.router)
app.include_router(gallery.router)
app.include_router(customer.router)
app.include_router(analytics.router)


# --------------- Public Routes --------------- #

@app.get("/")
def health_check():
    return {"status": "ok", "message": "THE HAIR ENGINEER API is running"}


@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("THE HAIR ENGINEER starting up (Phase 2)...")
    logger.info("=" * 60)
