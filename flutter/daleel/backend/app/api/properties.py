from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from .. import schemas as s
from ..services import properties as svc
from ..services.common import get_property
from .deps import get_db

router = APIRouter(prefix="/api/properties", tags=["Properties"])


@router.get("", response_model=s.Page)
def search(q: str | None = None, property_type: s.PropertyType | None = None, location: str | None = None,
           min_price: int | None = Query(None, ge=0), max_price: int | None = Query(None, ge=0),
           min_bedrooms: int | None = Query(None, ge=0), max_bedrooms: int | None = Query(None, ge=0),
           min_area: float | None = Query(None, ge=0), max_area: float | None = Query(None, ge=0),
           availability: s.Availability | None = None,
           sort: str = Query("id", pattern="^(id|price_asc|price_desc|area_desc)$"),
           limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    items, total = svc.search(db, q, property_type, location, min_price, max_price, min_bedrooms, max_bedrooms,
                              min_area, max_area, availability, sort, limit, offset)
    return s.Page(items=[s.PropertyOut.model_validate(i) for i in items], total=total, limit=limit, offset=offset)


@router.post("", response_model=s.PropertyOut, status_code=201)
def create(body: s.PropertyCreate, db: Session = Depends(get_db)):
    return svc.create(db, body)


@router.get("/{property_id}", response_model=s.PropertyOut)
def get(property_id: int, db: Session = Depends(get_db)):
    return get_property(db, property_id)


@router.patch("/{property_id}", response_model=s.PropertyOut)
def update(property_id: int, body: s.PropertyUpdate, db: Session = Depends(get_db)):
    return svc.update(db, property_id, body)


@router.delete("/{property_id}", status_code=204)
def delete(property_id: int, db: Session = Depends(get_db)):
    svc.delete(db, property_id)
    return Response(status_code=204)
