from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from .. import schemas as s
from ..services import consent, crm, followups, leads
from .deps import get_db

router = APIRouter(prefix="/api/leads", tags=["Leads & CRM"])


@router.get("", response_model=s.Page)
def list_leads(q: str | None = None, status: s.LeadStatus | None = None, priority: s.Priority | None = None,
               limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    items, total = leads.list_leads(db, q, status, priority, limit, offset)
    return s.Page(items=[s.LeadOut.model_validate(i) for i in items], total=total, limit=limit, offset=offset)


@router.post("", response_model=s.LeadOut, status_code=201)
def create_lead(body: s.LeadCreate, db: Session = Depends(get_db)):
    return leads.create_lead(db, body)


@router.get("/{lead_id}", response_model=s.LeadOut)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    from ..services.common import get_lead as g
    return g(db, lead_id)


@router.patch("/{lead_id}", response_model=s.LeadOut)
def update_lead(lead_id: int, body: s.LeadUpdate, db: Session = Depends(get_db)):
    return leads.update_lead(db, lead_id, body)


@router.delete("/{lead_id}", status_code=204)
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    leads.delete_lead(db, lead_id)
    return Response(status_code=204)


@router.put("/{lead_id}/qualification", response_model=s.LeadOut)
def update_qualification(lead_id: int, body: s.QualificationUpdate, db: Session = Depends(get_db)):
    return leads.update_lead(db, lead_id, body, activity_type="qualification_updated")


@router.put("/{lead_id}/stage", response_model=s.LeadOut)
def update_stage(lead_id: int, body: s.StageUpdate, db: Session = Depends(get_db)):
    return leads.update_lead(db, lead_id, body)


@router.put("/{lead_id}/consent", response_model=s.LeadOut)
def update_consent(lead_id: int, body: s.ConsentUpdate, db: Session = Depends(get_db)):
    return consent.update_consent(db, lead_id, body)


@router.get("/{lead_id}/crm", response_model=s.CrmOut)
def crm_view(lead_id: int, db: Session = Depends(get_db)):
    return crm.lead_view(db, lead_id)


@router.get("/{lead_id}/activities", response_model=list[s.ActivityOut])
def list_activities(lead_id: int, db: Session = Depends(get_db)):
    return crm.activities(db, lead_id)


@router.post("/{lead_id}/activities", response_model=s.ActivityOut, status_code=201)
def add_activity(lead_id: int, body: s.ActivityCreate, db: Session = Depends(get_db)):
    return crm.add_note(db, lead_id, body)


@router.get("/{lead_id}/follow-ups", response_model=s.FollowUpOut)
def follow_ups(lead_id: int, db: Session = Depends(get_db)):
    return followups.suggest(db, lead_id)
