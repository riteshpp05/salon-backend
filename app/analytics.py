"""
app/analytics.py
Calculates and formats all business intelligence metrics for the analytics dashboard.
"""
from datetime import date, datetime, timedelta
from typing import Dict, List, Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Booking, Customer, Stylist, Service

ACTIVE_STATUSES = ["Pending", "Confirmed"]
REVENUE_STATUSES = ["Confirmed", "Completed"]

def get_date_range(days: int = 30) -> tuple[datetime, datetime]:
    end = datetime.now()
    start = end - timedelta(days=days)
    return start, end

def get_business_overview(db: Session) -> Dict[str, Any]:
    """Calculates Revenue, Growth, LTV, etc."""
    today = date.today().isoformat()
    thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()
    sixty_days_ago = (date.today() - timedelta(days=60)).isoformat()

    all_rev_bookings = db.query(Booking).filter(Booking.status.in_(REVENUE_STATUSES)).all()
    
    # Revenue calculations
    total_rev = sum(int(b.price) for b in all_rev_bookings if str(b.price).isdigit())
    
    current_month_rev = sum(
        int(b.price) for b in all_rev_bookings 
        if b.appointment_date >= thirty_days_ago and str(b.price).isdigit()
    )
    
    last_month_rev = sum(
        int(b.price) for b in all_rev_bookings 
        if sixty_days_ago <= b.appointment_date < thirty_days_ago and str(b.price).isdigit()
    )
    
    # Growth %
    growth = 0.0
    if last_month_rev > 0:
        growth = ((current_month_rev - last_month_rev) / last_month_rev) * 100
    
    # Average Booking Value (ABV)
    abv = current_month_rev / len([b for b in all_rev_bookings if b.appointment_date >= thirty_days_ago]) if [b for b in all_rev_bookings if b.appointment_date >= thirty_days_ago] else 0

    # Customers & LTV
    unique_customers = db.query(Customer).count()
    ltv = total_rev / unique_customers if unique_customers > 0 else 0

    # Repeat Rate
    # Find customers with >1 booking
    customer_counts = db.query(Booking.customer_id, func.count(Booking.id)).group_by(Booking.customer_id).all()
    repeat_customers = len([c for c in customer_counts if c[1] > 1 and c[0] is not None])
    repeat_rate = (repeat_customers / unique_customers * 100) if unique_customers > 0 else 0

    return {
        "monthly_revenue": current_month_rev,
        "revenue_growth": round(growth, 1),
        "average_booking_value": round(abv, 0),
        "customer_ltv": round(ltv, 0),
        "repeat_rate": round(repeat_rate, 1),
        "total_revenue": total_rev
    }

def get_chart_data(db: Session) -> Dict[str, Any]:
    """Generates data arrays for Chart.js"""
    thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()
    
    # 1. Revenue Trend (Last 30 days)
    daily_rev = db.query(Booking.appointment_date, func.sum(Booking.price)).filter(
        Booking.status.in_(REVENUE_STATUSES),
        Booking.appointment_date >= thirty_days_ago
    ).group_by(Booking.appointment_date).order_by(Booking.appointment_date).all()
    
    # For SQLite, sum(price) might be tricky if price is stored as string, but we can do it in memory since dataset is small
    recent_bookings = db.query(Booking).filter(
        Booking.appointment_date >= thirty_days_ago,
        Booking.status.in_(REVENUE_STATUSES)
    ).all()
    
    revenue_trend = {}
    for b in recent_bookings:
        if str(b.price).isdigit():
            revenue_trend[b.appointment_date] = revenue_trend.get(b.appointment_date, 0) + int(b.price)
    
    trend_labels = sorted(revenue_trend.keys())
    trend_data = [revenue_trend[k] for k in trend_labels]

    # 2. Service Popularity
    service_pop = db.query(Booking.service, func.count(Booking.id)).filter(
        Booking.status.in_(REVENUE_STATUSES)
    ).group_by(Booking.service).all()
    
    service_labels = [s[0] for s in service_pop]
    service_data = [s[1] for s in service_pop]

    return {
        "revenue_trend": {"labels": trend_labels, "data": trend_data},
        "service_popularity": {"labels": service_labels, "data": service_data}
    }

def get_staff_analytics(db: Session) -> List[Dict[str, Any]]:
    stylists = db.query(Stylist).filter(Stylist.is_active == True).all()
    all_rev_bookings = db.query(Booking).filter(Booking.status.in_(REVENUE_STATUSES)).all()
    
    result = []
    for s in stylists:
        stylist_bookings = [b for b in all_rev_bookings if b.stylist_id == s.id]
        rev = sum(int(b.price) for b in stylist_bookings if str(b.price).isdigit())
        total_b = len(stylist_bookings)
        # Utilization mock calculation based on a standard 8 slots/day, 30 days = 240 slots.
        utilization = min(round((total_b / 240) * 100, 1), 100) if total_b > 0 else 0
        
        result.append({
            "name": s.full_name,
            "role": s.role,
            "appointments": total_b,
            "revenue": rev,
            "utilization": utilization
        })
    
    # Sort by revenue descending
    result.sort(key=lambda x: x["revenue"], reverse=True)
    return result

def generate_business_insights(db: Session) -> List[str]:
    """Rule-based engine to generate business insights."""
    insights = []
    
    thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()
    sixty_days_ago = (date.today() - timedelta(days=60)).isoformat()
    
    all_rev = db.query(Booking).filter(Booking.status.in_(REVENUE_STATUSES)).all()
    
    cur_month = [b for b in all_rev if b.appointment_date >= thirty_days_ago]
    last_month = [b for b in all_rev if sixty_days_ago <= b.appointment_date < thirty_days_ago]
    
    cur_rev = sum(int(b.price) for b in cur_month if str(b.price).isdigit())
    last_rev = sum(int(b.price) for b in last_month if str(b.price).isdigit())
    
    # Revenue Insight
    if last_rev > 0:
        growth = ((cur_rev - last_rev) / last_rev) * 100
        if growth > 0:
            insights.append(f"Trending Up: Revenue increased by {growth:.1f}% over the last 30 days.")
        elif growth < 0:
            insights.append(f"Attention: Revenue is down by {abs(growth):.1f}% compared to the previous month.")
    elif cur_rev > 0:
        insights.append("Great start! You generated your first revenue this month.")
        
    # Service Insight
    services = db.query(Booking.service, func.count(Booking.id)).filter(
        Booking.appointment_date >= thirty_days_ago, Booking.status.in_(REVENUE_STATUSES)
    ).group_by(Booking.service).order_by(func.count(Booking.id).desc()).all()
    
    if services:
        top_service = services[0][0]
        insights.append(f"Top Performer: '{top_service}' is your most popular service this month.")
        
    # Peak Hour Insight
    slots = db.query(Booking.time_slot, func.count(Booking.id)).filter(
        Booking.status.in_(ACTIVE_STATUSES)
    ).group_by(Booking.time_slot).order_by(func.count(Booking.id).desc()).all()
    
    if slots:
        top_slot = slots[0][0]
        insights.append(f"Peak Demand: '{top_slot}' is your most booked time slot. Consider staffing up during this hour.")
        
    # Retention Insight
    if cur_month:
        repeat = len([b for b in cur_month if b.customer_id is not None])
        if repeat > 0:
            rate = (repeat / len(cur_month)) * 100
            if rate > 50:
                insights.append(f"Strong Loyalty: {rate:.1f}% of recent bookings were from returning customers with accounts.")
                
    if not insights:
        insights.append("Not enough data yet to generate insights. Keep gathering bookings!")
        
    return insights

def get_export_data(db: Session, export_type: str) -> List[List[str]]:
    """Returns rows for CSV export."""
    if export_type == "revenue":
        bookings = db.query(Booking).filter(Booking.status.in_(REVENUE_STATUSES)).order_by(Booking.appointment_date.desc()).all()
        data = [["Date", "Customer", "Service", "Price", "Stylist ID", "Status"]]
        for b in bookings:
            data.append([b.appointment_date, b.customer_name, b.service, b.price, str(b.stylist_id or ""), b.status])
        return data
        
    elif export_type == "bookings":
        bookings = db.query(Booking).order_by(Booking.created_at.desc()).all()
        data = [["Created At", "Date", "Slot", "Customer", "Phone", "Service", "Status"]]
        for b in bookings:
            data.append([str(b.created_at), b.appointment_date, b.time_slot, b.customer_name, b.phone, b.service, b.status])
        return data
        
    elif export_type == "customers":
        customers = db.query(Customer).order_by(Customer.created_at.desc()).all()
        data = [["Joined", "Name", "Phone", "Loyalty Points", "Preferred Stylist ID"]]
        for c in customers:
            data.append([str(c.created_at), c.full_name, c.phone, str(c.loyalty_points), str(c.preferred_stylist_id or "")])
        return data
        
    return []
