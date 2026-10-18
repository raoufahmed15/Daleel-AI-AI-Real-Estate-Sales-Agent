from sqlalchemy import or_, select, func
from sqlalchemy.orm import Session

from ..errors import AppError
from ..models import Lead
from ..schemas import QUALIFICATION_FIELDS
from .common import get_lead, log_activity


def list_leads(db: Session, q=None, status=None, priority=None, limit=50, offset=0):
    stmt = select(Lead)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Lead.name.ilike(like), Lead.phone.ilike(like), Lead.email.ilike(like),
                              Lead.preferred_location.ilike(like)))
    if status:
        stmt = stmt.where(Lead.status == status)
    if priority:
        stmt = stmt.where(Lead.priority == priority)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(Lead.id.desc()).limit(limit).offset(offset)).all()
    return items, total


def _check_money(lead: Lead):
    if lead.budget is not None and lead.down_payment is not None and lead.down_payment > lead.budget:
        raise AppError(422, "validation_error", "down_payment cannot exceed budget",
                       [{"field": "down_payment", "message": "cannot exceed budget"}])


def create_lead(db: Session, data) -> Lead:
    lead = Lead(**data.model_dump())
    _check_money(lead)
    db.add(lead)
    db.flush()
    log_activity(db, lead.id, "lead_created", f"Lead '{lead.name}' created (status: {lead.status})")
    db.commit()
    return lead


def update_lead(db: Session, lead_id: int, data, activity_type="lead_updated") -> Lead:
    lead = get_lead(db, lead_id)
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is None:
        raise AppError(422, "validation_error", "name cannot be empty")
    old_status = lead.status
    changed = []
    for k, v in changes.items():
        if getattr(lead, k) != v:
            setattr(lead, k, v)
            changed.append(k)
    _check_money(lead)
    if changed:
        log_activity(db, lead.id, activity_type, "Updated fields: " + ", ".join(changed))
        if "status" in changed:
            log_activity(db, lead.id, "stage_changed", f"Funnel stage: {old_status} -> {lead.status}")
    db.commit()
    return lead


def set_stage(db: Session, lead_id: int, status: str) -> Lead:
    from ..schemas import StageUpdate
    return update_lead(db, lead_id, StageUpdate(status=status))


def delete_lead(db: Session, lead_id: int):
    lead = get_lead(db, lead_id)
    db.delete(lead)
    db.commit()


def missing_qualification(lead: Lead) -> list[str]:
    return [f for f in QUALIFICATION_FIELDS if getattr(lead, f) is None]
