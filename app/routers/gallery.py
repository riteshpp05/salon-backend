"""
routers/gallery.py — Before & After Gallery Management APIs
"""
import io
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app import crud, schemas
from app.auth import require_admin_api
from app.database import SessionLocal

router = APIRouter()

GALLERY_DIR = os.path.join("app", "static", "gallery")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _process_and_save_image(content: bytes, subfolder: str, prefix: str) -> str:
    """
    Process uploaded image with Pillow:
    - Validate size
    - Resize to max 1200px width
    - Convert to WebP at 85% quality
    - Save thumbnail (400px) in thumbs/
    Returns the saved filename.
    """
    from PIL import Image

    img = Image.open(io.BytesIO(content)).convert("RGB")

    # Full-size version (max 1200px wide)
    img_full = img.copy()
    if img_full.width > 1200:
        ratio = 1200 / img_full.width
        img_full = img_full.resize(
            (1200, int(img_full.height * ratio)), Image.LANCZOS
        )

    filename = f"{prefix}_{uuid.uuid4().hex[:10]}.webp"

    # Save full image
    full_path = os.path.join(GALLERY_DIR, subfolder, filename)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    img_full.save(full_path, "WEBP", quality=85)

    # Save thumbnail (400px wide)
    img_thumb = img.copy()
    if img_thumb.width > 400:
        ratio = 400 / img_thumb.width
        img_thumb = img_thumb.resize(
            (400, int(img_thumb.height * ratio)), Image.LANCZOS
        )
    thumb_path = os.path.join(GALLERY_DIR, "thumbs", filename)
    os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
    img_thumb.save(thumb_path, "WEBP", quality=80)

    return filename


def _build_gallery_response(item) -> dict:
    base = "/static/gallery"
    return {
        "id": item.id,
        "title": item.title,
        "description": item.description,
        "service_type": item.service_type,
        "before_image": f"{base}/before/{item.before_image}" if item.before_image else "",
        "before_thumb": f"{base}/thumbs/{item.before_image}" if item.before_image else "",
        "after_image": f"{base}/after/{item.after_image}" if item.after_image else "",
        "after_thumb": f"{base}/thumbs/{item.after_image}" if item.after_image else "",
        "display_order": item.display_order,
        "is_published": item.is_published,
    }


# ── Public ────────────────────────────────────────────────────────────────────

@router.get("/api/gallery")
def list_gallery(
    service: str = None,
    db: Session = Depends(get_db),
):
    """Public: return published gallery items, optionally filtered by service_type."""
    items = crud.get_gallery_items(db, published_only=True, service_type=service)
    return [_build_gallery_response(i) for i in items]


@router.get("/api/gallery/types")
def gallery_types(db: Session = Depends(get_db)):
    """Public: return unique service types for filter buttons."""
    from app.models import GalleryItem
    types = (
        db.query(GalleryItem.service_type)
        .filter(GalleryItem.is_published == True)
        .distinct()
        .all()
    )
    return ["All"] + [t[0] for t in types if t[0]]


# ── Admin Only ────────────────────────────────────────────────────────────────

@router.get("/api/gallery/admin")
def list_gallery_admin(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    """Admin: return all gallery items including unpublished."""
    items = crud.get_gallery_items(db, published_only=False)
    return [_build_gallery_response(i) for i in items]


@router.post("/api/gallery")
def create_gallery_item(
    data: schemas.GalleryItemCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    item = crud.create_gallery_item(db, data)
    return _build_gallery_response(item)


@router.put("/api/gallery/{item_id}")
def update_gallery_item(
    item_id: int,
    data: schemas.GalleryItemUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    item = crud.update_gallery_item(db, item_id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Gallery item not found")
    return _build_gallery_response(item)


@router.delete("/api/gallery/{item_id}")
def delete_gallery_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    item = crud.delete_gallery_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Gallery item not found")
    return {"message": "Gallery item deleted"}


@router.post("/api/gallery/{item_id}/before-image")
async def upload_before_image(
    item_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    item = crud.get_gallery_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Gallery item not found")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid file type '{ext}'.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB).")

    try:
        filename = _process_and_save_image(content, "before", f"before_{item_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image processing failed: {e}")

    crud.update_gallery_image(db, item_id, "before", filename)
    return {"message": "Before image uploaded", "url": f"/static/gallery/before/{filename}"}


@router.post("/api/gallery/{item_id}/after-image")
async def upload_after_image(
    item_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    item = crud.get_gallery_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Gallery item not found")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid file type '{ext}'.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB).")

    try:
        filename = _process_and_save_image(content, "after", f"after_{item_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image processing failed: {e}")

    crud.update_gallery_image(db, item_id, "after", filename)
    return {"message": "After image uploaded", "url": f"/static/gallery/after/{filename}"}


@router.patch("/api/gallery/{item_id}/publish")
def toggle_publish(
    item_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    item = crud.toggle_gallery_publish(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Gallery item not found")
    return {"message": f"Gallery item {'published' if item.is_published else 'unpublished'}", "is_published": item.is_published}


@router.post("/api/gallery/reorder")
def reorder_gallery(
    order_map: dict[int, int],
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api),
):
    crud.reorder_gallery(db, order_map)
    return {"message": "Gallery order updated"}
