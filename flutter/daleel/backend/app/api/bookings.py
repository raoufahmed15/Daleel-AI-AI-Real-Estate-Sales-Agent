from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas as s
from ..services import bookings as svc
from .deps import get_db

router = APIRouter(prefix="/api/bookings", tags=["Simulated Bookings"])


@router.get("/slots", response_model=list[s.Slot])
def slots(property_id: int, day: date, lead_id: int | None = None, db: Session = Depends(get_db)):
    return svc.slots_for(db, property_id, day, lead_id)


@router.get("", response_model=list[s.BookingOut])
def list_bookings(status: str | None = None, lead_id: int | None = None, property_id: int | None = None,
                  upcoming: bool = False, db: Session = Depends(get_db)):
    return [svc.to_out(b) for b in svc.list_bookings(db, status, lead_id, property_id, upcoming)]


@router.post("", response_model=s.BookingOut, status_code=201)
def create(body: s.BookingCreate, db: Session = Depends(get_db)):
    return svc.to_out(svc.create(db, body))


@router.post("/{booking_id}/cancel", response_model=s.BookingOut)
def cancel(booking_id: int, body: s.BookingCancel | None = None, db: Session = Depends(get_db)):
    return svc.to_out(svc.cancel(db, booking_id, body.reason if body else None))
