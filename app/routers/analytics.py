"""
routers/analytics.py
Serves the analytics data to the frontend and handles CSV exports.
"""
import io
import csv
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.auth import require_admin_api
from app import analytics

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/api/analytics/overview")
def get_overview(db: Session = Depends(get_db), _: None = Depends(require_admin_api)):
    return analytics.get_business_overview(db)


@router.get("/api/analytics/charts")
def get_charts(db: Session = Depends(get_db), _: None = Depends(require_admin_api)):
    return analytics.get_chart_data(db)


@router.get("/api/analytics/staff")
def get_staff_stats(db: Session = Depends(get_db), _: None = Depends(require_admin_api)):
    return analytics.get_staff_analytics(db)


@router.get("/api/analytics/insights")
def get_insights(db: Session = Depends(get_db), _: None = Depends(require_admin_api)):
    return {"insights": analytics.generate_business_insights(db)}


@router.get("/api/analytics/export/{export_type}")
def export_csv(export_type: str, db: Session = Depends(get_db), _: None = Depends(require_admin_api)):
    if export_type not in ["revenue", "bookings", "customers"]:
        raise HTTPException(status_code=400, detail="Invalid export type")
        
    data = analytics.get_export_data(db, export_type)
    
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerows(data)
    
    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    date_str = datetime.now().strftime("%Y-%m-%d")
    response.headers["Content-Disposition"] = f"attachment; filename={export_type}_report_{date_str}.csv"
    
    return response
