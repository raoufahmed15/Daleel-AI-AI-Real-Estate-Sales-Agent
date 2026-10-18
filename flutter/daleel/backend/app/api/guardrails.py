from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas as s
from ..services import guardrails as svc
from .deps import get_db

router = APIRouter(prefix="/api/guardrails", tags=["Guardrails"])


@router.get("/discount-bands", response_model=list[s.DiscountBandOut])
def list_bands(db: Session = Depends(get_db)):
    return svc.list_bands(db)


@router.post("/discount-bands", response_model=s.DiscountBandOut, status_code=201)
def create_band(body: s.DiscountBandIn, db: Session = Depends(get_db)):
    return svc.create_band(db, body)


@router.put("/discount-bands/{band_id}", response_model=s.DiscountBandOut)
def update_band(band_id: int, body: s.DiscountBandIn, db: Session = Depends(get_db)):
    return svc.update_band(db, band_id, body)
