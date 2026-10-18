from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas as s
from ..services import handoffs as svc
from .deps import get_db

router = APIRouter(prefix="/api/handoffs", tags=["Human Handoff"])


@router.get("", response_model=list[s.HandoffOut])
def list_handoffs(status: s.HandoffStatus | None = None, lead_id: int | None = None,
                  category: s.HandoffCategory | None = None, db: Session = Depends(get_db)):
    return [svc.to_out(db, h, with_events=False) for h in svc.list_handoffs(db, status, lead_id, category)]


@router.post("", response_model=s.HandoffOut, status_code=201)
def create(body: s.HandoffCreate, db: Session = Depends(get_db)):
    return svc.to_out(db, svc.create(db, body))


@router.get("/{handoff_id}", response_model=s.HandoffOut)
def get(handoff_id: int, db: Session = Depends(get_db)):
    return svc.to_out(db, svc.get(db, handoff_id))


@router.patch("/{handoff_id}", response_model=s.HandoffOut)
def update(handoff_id: int, body: s.HandoffUpdate, db: Session = Depends(get_db)):
    return svc.to_out(db, svc.update(db, handoff_id, body))
