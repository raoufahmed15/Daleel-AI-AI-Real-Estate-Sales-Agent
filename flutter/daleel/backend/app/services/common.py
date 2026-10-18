from sqlalchemy.orm import Session

from ..errors import AppError, not_found
from ..models import Activity, Lead, Property


def log_activity(db: Session, lead_id, type_, description, handoff_id=None, actor="staff") -> Activity:
    a = Activity(lead_id=lead_id, handoff_id=handoff_id, type=type_, description=description, actor=actor)
    db.add(a)
    return a


def get_lead(db: Session, lead_id: int) -> Lead:
    lead = db.get(Lead, lead_id)
    if not lead:
        raise not_found("Lead", lead_id)
    return lead


def get_property(db: Session, property_id: int) -> Property:
    p = db.get(Property, property_id)
    if not p:
        raise not_found("Property", property_id)
    return p


def assert_can_contact(lead: Lead):
    """Central consent gate. Every outbound or simulated-outbound action must call this."""
    if lead.opted_out:
        raise AppError(409, "lead_opted_out", "This lead has opted out. No follow-up or outbound action is allowed.")
    if lead.consent_status == "denied":
        raise AppError(409, "consent_denied", "This lead denied consent. No follow-up or outbound action is allowed.")
