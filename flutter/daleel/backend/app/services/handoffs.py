from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import AppError, not_found
from ..models import Activity, Handoff
from ..schemas import ActivityOut, HandoffOut
from .common import get_lead, log_activity

TRANSITIONS = {
    "open": {"in_review", "resolved", "dismissed"},
    "in_review": {"open", "resolved", "dismissed"},
    "resolved": {"open"},
    "dismissed": {"open"},
}


def to_out(db: Session, h: Handoff, with_events=True) -> HandoffOut:
    events = []
    if with_events:
        rows = db.scalars(select(Activity).where(Activity.handoff_id == h.id).order_by(Activity.id.desc())).all()
        events = [ActivityOut.model_validate(r) for r in rows]
    return HandoffOut(id=h.id, lead_id=h.lead_id, lead_name=h.lead.name if h.lead else None, category=h.category,
                      reason=h.reason, status=h.status, assigned_to=h.assigned_to, created_at=h.created_at,
                      updated_at=h.updated_at, events=events)


def create(db: Session, data) -> Handoff:
    lead = get_lead(db, data.lead_id) if data.lead_id else None
    h = Handoff(lead_id=data.lead_id, category=data.category, reason=data.reason)
    db.add(h)
    db.flush()
    log_activity(db, data.lead_id, "handoff_created", f"Handoff #{h.id} ({data.category}): {data.reason}",
                 handoff_id=h.id)
    db.commit()
    return h


def get(db: Session, handoff_id: int) -> Handoff:
    h = db.get(Handoff, handoff_id)
    if not h:
        raise not_found("Handoff", handoff_id)
    return h


def update(db: Session, handoff_id: int, data) -> Handoff:
    h = get(db, handoff_id)
    if data.status is None and data.assigned_to is None and not data.note:
        raise AppError(422, "validation_error", "Provide status, assigned_to and/or note")
    if data.status and data.status != h.status:
        if data.status not in TRANSITIONS[h.status]:
            raise AppError(409, "invalid_transition", f"Cannot move handoff from {h.status} to {data.status}")
        log_activity(db, h.lead_id, "handoff_status", f"Handoff #{h.id}: {h.status} -> {data.status}", handoff_id=h.id)
        h.status = data.status
    if data.assigned_to is not None and data.assigned_to != h.assigned_to:
        log_activity(db, h.lead_id, "handoff_assigned", f"Handoff #{h.id} assigned to {data.assigned_to or 'nobody'}",
                     handoff_id=h.id)
        h.assigned_to = data.assigned_to or None
    if data.note:
        log_activity(db, h.lead_id, "handoff_note", data.note, handoff_id=h.id)
    db.commit()
    return h


def list_handoffs(db: Session, status=None, lead_id=None, category=None):
    stmt = select(Handoff)
    if status:
        stmt = stmt.where(Handoff.status == status)
    if lead_id:
        stmt = stmt.where(Handoff.lead_id == lead_id)
    if category:
        stmt = stmt.where(Handoff.category == category)
    return db.scalars(stmt.order_by(Handoff.id.desc())).all()
