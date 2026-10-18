from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Activity, Booking, Handoff, utcnow
from ..schemas import FollowUpOut, FollowUpSuggestion
from .common import assert_can_contact, get_lead
from .leads import missing_qualification

LABELS = {"budget": "budget", "preferred_location": "preferred location", "property_type": "property type",
          "down_payment": "down payment", "monthly_installment": "monthly installment capacity",
          "purchase_timeline": "purchase timeline", "purchase_purpose": "purchase purpose (live or invest)"}


def suggest(db: Session, lead_id: int) -> FollowUpOut:
    lead = get_lead(db, lead_id)
    assert_can_contact(lead)  # raises for opted-out / denied leads
    s: list[FollowUpSuggestion] = []
    missing = missing_qualification(lead)
    if missing:
        s.append(FollowUpSuggestion(kind="collect_qualification",
                                    text="Ask the lead about: " + ", ".join(LABELS[m] for m in missing) + ".",
                                    reason="These qualification fields are empty."))
    open_h = db.scalar(select(func.count()).select_from(Handoff)
                       .where(Handoff.lead_id == lead.id, Handoff.status.in_(["open", "in_review"])))
    if open_h:
        s.append(FollowUpSuggestion(kind="await_human", text="Hold commercial follow-up until the human reviewer responds.",
                                    reason=f"{open_h} handoff case(s) are still pending."))
    upcoming = db.scalars(select(Booking).where(Booking.lead_id == lead.id, Booking.status == "scheduled",
                                                Booking.start >= utcnow()).order_by(Booking.start)).first()
    if upcoming:
        s.append(FollowUpSuggestion(kind="viewing_reminder",
                                    text=f"Prepare a reminder for the simulated viewing on {upcoming.start:%Y-%m-%d %H:%M}.",
                                    reason="A simulated viewing is scheduled."))
    elif lead.status in ("qualified", "contacted") and not missing:
        s.append(FollowUpSuggestion(kind="offer_viewing", text="Offer to schedule a (simulated) viewing.",
                                    reason="Lead is qualified and has no upcoming viewing."))
    last = db.scalar(select(func.max(Activity.created_at)).where(Activity.lead_id == lead.id))
    if last and last < utcnow() - timedelta(days=7) and lead.status not in ("won", "lost"):
        s.append(FollowUpSuggestion(kind="check_in", text="Send a short check-in (staff to send manually).",
                                    reason="No CRM activity in the last 7 days."))
    if lead.next_steps:
        s.append(FollowUpSuggestion(kind="manual_next_step", text=lead.next_steps, reason="Next step recorded by staff."))
    if not s:
        s.append(FollowUpSuggestion(kind="none", text="No follow-up is suggested right now.",
                                    reason="Nothing pending based on stored records."))
    warning = "Consent has not been recorded for this lead; confirm consent before any real outreach." \
        if lead.consent_status == "unknown" else None
    return FollowUpOut(lead_id=lead.id, consent_status=lead.consent_status, warning=warning, suggestions=s)
