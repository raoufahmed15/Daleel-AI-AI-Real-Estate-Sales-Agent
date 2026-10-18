from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Activity, Booking, Handoff, Lead, Property, utcnow
from ..schemas import LEAD_STATUSES, QUALIFICATION_FIELDS


def metrics(db: Session) -> dict:
    count = lambda stmt: db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    by_status = dict.fromkeys(LEAD_STATUSES, 0)
    for st, n in db.execute(select(Lead.status, func.count()).group_by(Lead.status)):
        by_status[st] = n
    complete = count(select(Lead.id).where(*[getattr(Lead, f).is_not(None) for f in QUALIFICATION_FIELDS]))
    prop_by_av = {"available": 0, "reserved": 0, "sold": 0}
    for av, n in db.execute(select(Property.availability, func.count()).group_by(Property.availability)):
        prop_by_av[av] = n
    now = utcnow()
    return {
        "calculated": {
            "leads_total": count(select(Lead.id)),
            "leads_by_status": by_status,
            "leads_opted_out": count(select(Lead.id).where(Lead.opted_out.is_(True))),
            "leads_fully_qualified": complete,
            "properties_total": count(select(Property.id)),
            "properties_available": prop_by_av["available"],
            "properties_by_availability": prop_by_av,
            "bookings_upcoming": count(select(Booking.id).where(Booking.status == "scheduled", Booking.start >= now)),
            "bookings_scheduled_total": count(select(Booking.id).where(Booking.status == "scheduled")),
            "bookings_cancelled": count(select(Booking.id).where(Booking.status == "cancelled")),
            "handoffs_pending": count(select(Handoff.id).where(Handoff.status.in_(["open", "in_review"]))),
            "handoffs_total": count(select(Handoff.id)),
            "crm_activities_total": count(select(Activity.id)),
        },
        "unavailable_ai_metrics": [
            {"name": "Lead scores", "status": "not_implemented", "module": "lead_scoring"},
            {"name": "Recommendation match rate", "status": "not_implemented", "module": "recommendation_engine"},
            {"name": "RAG answer quality", "status": "not_implemented", "module": "rag"},
        ],
    }
