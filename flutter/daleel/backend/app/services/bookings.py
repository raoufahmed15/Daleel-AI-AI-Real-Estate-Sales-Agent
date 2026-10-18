from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import AppError, not_found
from ..models import Booking, utcnow
from ..schemas import BookingOut, Slot
from .common import assert_can_contact, get_lead, get_property, log_activity

SLOT_HOURS = list(range(10, 17))  # 10:00 .. 16:00 start, 60 min each
SLOT_MINUTES = 60


def to_out(b: Booking) -> BookingOut:
    return BookingOut(id=b.id, lead_id=b.lead_id, lead_name=b.lead.name, property_id=b.property_id,
                      property_title=b.property.title, start=b.start, end=b.end, status=b.status,
                      simulated=True, cancel_reason=b.cancel_reason, created_at=b.created_at)


def _overlap(db, start, end, **filters):
    stmt = select(Booking).where(Booking.status == "scheduled", Booking.start < end, Booking.end > start)
    for k, v in filters.items():
        stmt = stmt.where(getattr(Booking, k) == v)
    return db.scalars(stmt).first()


def slots_for(db: Session, property_id: int, day: date, lead_id: int | None = None) -> list[Slot]:
    prop = get_property(db, property_id)
    out = []
    now = utcnow()
    for h in SLOT_HOURS:
        start = datetime.combine(day, time(h))
        end = start + timedelta(minutes=SLOT_MINUTES)
        reason = None
        if prop.availability != "available":
            reason = f"property_{prop.availability}"
        elif start <= now:
            reason = "past"
        elif _overlap(db, start, end, property_id=property_id):
            reason = "property_booked"
        elif lead_id and _overlap(db, start, end, lead_id=lead_id):
            reason = "lead_busy"
        out.append(Slot(start=start, end=end, available=reason is None, reason=reason))
    return out


def create(db: Session, data) -> Booking:
    lead = get_lead(db, data.lead_id)
    prop = get_property(db, data.property_id)
    assert_can_contact(lead)  # booking confirmations are simulated outbound actions
    start = data.start.replace(second=0, microsecond=0, tzinfo=None)
    if start.hour not in SLOT_HOURS or start.minute != 0:
        raise AppError(422, "invalid_slot", "Start must be an hourly slot between 10:00 and 16:00")
    if prop.availability != "available":
        raise AppError(409, "property_unavailable", f"Property is {prop.availability}; it cannot be booked")
    if start <= utcnow():
        raise AppError(422, "slot_in_past", "Cannot book a slot in the past")
    end = start + timedelta(minutes=SLOT_MINUTES)
    if _overlap(db, start, end, property_id=prop.id):
        raise AppError(409, "booking_conflict", "This property already has a booking in that slot")
    if _overlap(db, start, end, lead_id=lead.id):
        raise AppError(409, "booking_conflict", "This lead already has a booking in that slot")
    b = Booking(lead_id=lead.id, property_id=prop.id, start=start, end=end, simulated=True)
    db.add(b)
    db.flush()
    log_activity(db, lead.id, "booking_created", f"Simulated viewing booked: {prop.title} on {start:%Y-%m-%d %H:%M}")
    if lead.status in ("new", "contacted", "qualified"):
        log_activity(db, lead.id, "stage_changed", f"Funnel stage: {lead.status} -> viewing_scheduled")
        lead.status = "viewing_scheduled"
    db.commit()
    return b


def cancel(db: Session, booking_id: int, reason: str | None) -> Booking:
    b = db.get(Booking, booking_id)
    if not b:
        raise not_found("Booking", booking_id)
    if b.status == "cancelled":
        raise AppError(409, "already_cancelled", "Booking is already cancelled")
    b.status, b.cancel_reason = "cancelled", reason
    log_activity(db, b.lead_id, "booking_cancelled", f"Simulated viewing cancelled: {b.property.title} on {b.start:%Y-%m-%d %H:%M}")
    db.commit()
    return b


def list_bookings(db: Session, status=None, lead_id=None, property_id=None, upcoming=False):
    stmt = select(Booking)
    if status:
        stmt = stmt.where(Booking.status == status)
    if lead_id:
        stmt = stmt.where(Booking.lead_id == lead_id)
    if property_id:
        stmt = stmt.where(Booking.property_id == property_id)
    if upcoming:
        stmt = stmt.where(Booking.start >= utcnow(), Booking.status == "scheduled")
    return db.scalars(stmt.order_by(Booking.start.asc())).all()
