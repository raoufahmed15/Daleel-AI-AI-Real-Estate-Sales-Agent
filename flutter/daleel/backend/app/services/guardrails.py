from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import AppError, not_found
from ..models import DiscountBand
from ..schemas import DiscountBandIn


def list_bands(db: Session) -> list[DiscountBand]:
    return db.scalars(select(DiscountBand).order_by(DiscountBand.id.desc())).all()


def create_band(db: Session, data: DiscountBandIn) -> DiscountBand:
    if data.min_pct > data.max_pct:
        raise AppError(422, "validation_error", "min_pct cannot exceed max_pct")
    b = DiscountBand(**data.model_dump())
    db.add(b)
    db.commit()
    return b


def update_band(db: Session, band_id: int, data: DiscountBandIn) -> DiscountBand:
    b = db.get(DiscountBand, band_id)
    if not b:
        raise not_found("DiscountBand", band_id)
    if data.min_pct > data.max_pct:
        raise AppError(422, "validation_error", "min_pct cannot exceed max_pct")
    for k, v in data.model_dump().items():
        setattr(b, k, v)
    db.commit()
    return b
