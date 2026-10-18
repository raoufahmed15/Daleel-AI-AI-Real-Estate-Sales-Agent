from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Lead(Base):
    __tablename__ = "leads"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="new", index=True)  # funnel stage
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    # Qualification (all optional - never invented)
    budget: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    property_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    down_payment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_installment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    purchase_timeline: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Consent
    consent_status: Mapped[str] = mapped_column(String(10), default="unknown")
    opted_out: Mapped[bool] = mapped_column(Boolean, default=False)
    conversation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    activities = relationship("Activity", back_populates="lead", cascade="all, delete-orphan",
                              order_by="Activity.id.desc()")
    bookings = relationship("Booking", back_populates="lead", cascade="all, delete-orphan",
                            order_by="Booking.start.desc()")
    handoffs = relationship("Handoff", back_populates="lead", order_by="Handoff.id.desc()")


class Property(Base):
    __tablename__ = "properties"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    title: Mapped[str] = mapped_column(String(160))
    property_type: Mapped[str] = mapped_column(String(30), index=True)
    location: Mapped[str] = mapped_column(String(120), index=True)
    area_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    availability: Mapped[str] = mapped_column(String(15), default="available", index=True)
    delivery_date: Mapped[str | None] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    payment_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    start: Mapped[datetime] = mapped_column(DateTime, index=True)
    end: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(15), default="scheduled")  # scheduled | cancelled
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    lead = relationship("Lead", back_populates="bookings")
    property = relationship("Property")


class Handoff(Base):
    __tablename__ = "handoffs"
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(15), default="open", index=True)
    assigned_to: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    lead = relationship("Lead", back_populates="handoffs")


class Activity(Base):
    """CRM activity log; handoff events are activities with handoff_id set."""
    __tablename__ = "activities"
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), nullable=True, index=True)
    handoff_id: Mapped[int | None] = mapped_column(ForeignKey("handoffs.id", ondelete="CASCADE"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(40), default="staff")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    lead = relationship("Lead", back_populates="activities")
