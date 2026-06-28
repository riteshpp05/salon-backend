"""
routers/gallery.py — Before & After Gallery Management APIs
"""
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



def _build_gallery_response(item) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "description": item.description,
        "service_type": item.service_type,
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
