from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..errors import AppError
from ..models import Booking, Property
from .common import get_property


def search(db: Session, q=None, property_type=None, location=None, min_price=None, max_price=None,
           min_bedrooms=None, max_bedrooms=None, min_area=None, max_area=None, availability=None,
           sort="id", limit=50, offset=0):
    stmt = select(Property)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Property.title.ilike(like), Property.code.ilike(like), Property.location.ilike(like)))
    if property_type:
        stmt = stmt.where(Property.property_type == property_type)
    if location:
        stmt = stmt.where(Property.location.ilike(f"%{location.strip()}%"))
    if availability:
        stmt = stmt.where(Property.availability == availability)
    for col, lo, hi in ((Property.price, min_price, max_price), (Property.bedrooms, min_bedrooms, max_bedrooms),
                        (Property.area_sqm, min_area, max_area)):
        if lo is not None:
            stmt = stmt.where(col >= lo)
        if hi is not None:
            stmt = stmt.where(col <= hi)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    order = {"price_asc": Property.price.asc(), "price_desc": Property.price.desc(),
             "area_desc": Property.area_sqm.desc()}.get(sort, Property.id.asc())
    return db.scalars(stmt.order_by(order).limit(limit).offset(offset)).all(), total


def _next_code(db: Session) -> str:
    n = db.scalar(select(func.coalesce(func.max(Property.id), 0))) + 1
    code = f"DLL-{n:04d}"
    while db.scalar(select(Property.id).where(Property.code == code)):
        n += 1
        code = f"DLL-{n:04d}"
    return code


def create(db: Session, data) -> Property:
    values = data.model_dump()
    values["delivery_date"] = values["delivery_date"].isoformat() if values["delivery_date"] else None
    values["source_updated_at"] = values["source_updated_at"].isoformat() if values.get("source_updated_at") else None
    values["code"] = values["code"] or _next_code(db)
    if db.scalar(select(Property.id).where(Property.code == values["code"])):
        raise AppError(409, "duplicate_code", f"Property code {values['code']} already exists")
    p = Property(**values)
    db.add(p)
    db.commit()
    return p


def update(db: Session, property_id: int, data) -> Property:
    p = get_property(db, property_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        if k in ("delivery_date", "source_updated_at"):
            v = v.isoformat() if v else None
        if v is None and k in ("title", "property_type", "location", "availability"):
            raise AppError(422, "validation_error", f"{k} cannot be null")
        setattr(p, k, v)
    db.commit()
    return p


def delete(db: Session, property_id: int):
    p = get_property(db, property_id)
    active = db.scalar(select(func.count()).select_from(Booking)
                       .where(Booking.property_id == p.id, Booking.status == "scheduled"))
    if active:
        raise AppError(409, "property_has_bookings", "Cancel the scheduled bookings for this property first")
    db.query(Booking).filter(Booking.property_id == p.id).delete()
    db.delete(p)
    db.commit()
