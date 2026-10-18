from sqlalchemy.orm import Session

from ..errors import AppError
from .common import get_lead, log_activity


def update_consent(db: Session, lead_id: int, data):
    lead = get_lead(db, lead_id)
    if data.consent_status is None and data.opted_out is None:
        raise AppError(422, "validation_error", "Provide consent_status and/or opted_out")
    if data.consent_status is not None and data.consent_status != lead.consent_status:
        log_activity(db, lead.id, "consent_changed", f"Consent: {lead.consent_status} -> {data.consent_status}")
        lead.consent_status = data.consent_status
    if data.opted_out is not None and data.opted_out != lead.opted_out:
        lead.opted_out = data.opted_out
        log_activity(db, lead.id, "opt_out" if data.opted_out else "opt_in",
                     "Lead opted out of all follow-ups" if data.opted_out else "Opt-out removed by staff")
    db.commit()
    return lead
