from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Activity
from ..schemas import ActivityOut, CrmOut, LeadOut
from . import bookings as booking_svc
from . import handoffs as handoff_svc
from .common import get_lead, log_activity
from .leads import missing_qualification


def add_note(db: Session, lead_id: int, data) -> Activity:
    get_lead(db, lead_id)
    a = log_activity(db, lead_id, data.type, data.description)
    db.commit()
    return a


def activities(db: Session, lead_id: int, limit=100):
    get_lead(db, lead_id)
    return db.scalars(select(Activity).where(Activity.lead_id == lead_id).order_by(Activity.id.desc()).limit(limit)).all()


def lead_view(db: Session, lead_id: int) -> CrmOut:
    lead = get_lead(db, lead_id)
    missing = missing_qualification(lead)
    hs = [handoff_svc.to_out(db, h, with_events=False) for h in lead.handoffs]
    pending = [h for h in hs if h.status in ("open", "in_review")]
    return CrmOut(lead=LeadOut.model_validate(lead), qualification_complete=not missing, missing_qualification=missing,
                  activities=[ActivityOut.model_validate(a) for a in activities(db, lead_id)],
                  bookings=[booking_svc.to_out(b) for b in lead.bookings], handoffs=hs,
                  open_handoff_status=(pending[0].status if pending else None))
