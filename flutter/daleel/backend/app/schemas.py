import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

LeadStatus = Literal["new", "contacted", "qualified", "viewing_scheduled", "negotiation", "won", "lost"]
Priority = Literal["low", "medium", "high"]
PropertyType = Literal["apartment", "villa", "townhouse", "duplex", "studio", "penthouse", "chalet", "office"]
Timeline = Literal["immediate", "1_3_months", "3_6_months", "6_12_months", "over_12_months"]
Consent = Literal["unknown", "granted", "denied"]
Availability = Literal["available", "reserved", "sold"]
HandoffCategory = Literal["hot_lead", "complaint", "conflicting_commercial_info", "discount_request",
                          "legal_dispute", "data_deletion_request", "other"]
HandoffStatus = Literal["open", "in_review", "resolved", "dismissed"]

LEAD_STATUSES = ["new", "contacted", "qualified", "viewing_scheduled", "negotiation", "won", "lost"]
QUALIFICATION_FIELDS = ["budget", "preferred_location", "property_type", "down_payment",
                        "monthly_installment", "purchase_timeline", "purchase_purpose"]
LeadSource = Literal["ad", "project_page", "direct"]
LeadChannel = Literal["web_chat", "whatsapp_sandbox", "voice"]
PurchasePurpose = Literal["live", "invest"]
Readiness = Literal["off_plan", "ready_to_move"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _clean(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


def _check_phone(v):
    if v is not None and not re.fullmatch(r"\+?[0-9 \-]{6,30}", v):
        raise ValueError("phone must contain 6-30 digits, spaces or dashes (optional leading +)")
    return v


def _check_email(v):
    if v is not None and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
        raise ValueError("invalid email address")
    return v


class QualificationFields(BaseModel):
    budget: int | None = Field(None, ge=0)
    preferred_location: str | None = Field(None, max_length=120)
    property_type: PropertyType | None = None
    down_payment: int | None = Field(None, ge=0)
    monthly_installment: int | None = Field(None, ge=0)
    purchase_timeline: Timeline | None = None
    purchase_purpose: PurchasePurpose | None = None

    _c = field_validator("preferred_location", mode="before")(_clean)


class LeadBase(QualificationFields):
    name: str = Field(..., min_length=1, max_length=120)
    phone: str | None = Field(None, max_length=30)
    email: str | None = Field(None, max_length=160)
    status: LeadStatus = "new"
    priority: Priority = "medium"
    conversation_summary: str | None = None
    next_steps: str | None = None
    source: LeadSource | None = None
    channel: LeadChannel | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _name(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("phone", "email", "conversation_summary", "next_steps", mode="before")
    @classmethod
    def _opt(cls, v):
        return _clean(v)

    _v3 = field_validator("phone")(_check_phone)
    _v4 = field_validator("email")(_check_email)


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    phone: str | None = None
    email: str | None = None
    status: LeadStatus | None = None
    priority: Priority | None = None
    conversation_summary: str | None = None
    next_steps: str | None = None
    budget: int | None = Field(None, ge=0)
    preferred_location: str | None = Field(None, max_length=120)
    property_type: PropertyType | None = None
    down_payment: int | None = Field(None, ge=0)
    monthly_installment: int | None = Field(None, ge=0)
    purchase_timeline: Timeline | None = None
    purchase_purpose: PurchasePurpose | None = None
    source: LeadSource | None = None
    channel: LeadChannel | None = None

    _v1 = field_validator("phone", "email", "conversation_summary", "next_steps", mode="before")(_clean)
    _v3 = field_validator("phone")(_check_phone)
    _v4 = field_validator("email")(_check_email)


class QualificationUpdate(QualificationFields):
    pass


class ConsentUpdate(BaseModel):
    consent_status: Consent | None = None
    opted_out: bool | None = None


class StageUpdate(BaseModel):
    status: LeadStatus


class LeadOut(ORM):
    id: int
    name: str
    phone: str | None
    email: str | None
    status: str
    priority: str
    budget: int | None
    preferred_location: str | None
    property_type: str | None
    down_payment: int | None
    monthly_installment: int | None
    purchase_timeline: str | None
    purchase_purpose: str | None
    source: str | None
    channel: str | None
    consent_status: str
    opted_out: bool
    conversation_summary: str | None
    next_steps: str | None
    created_at: datetime
    updated_at: datetime


class Page(BaseModel):
    items: list
    total: int
    limit: int
    offset: int


class PropertyBase(BaseModel):
    code: str | None = Field(None, max_length=30)
    title: str = Field(..., min_length=1, max_length=160)
    property_type: PropertyType
    location: str = Field(..., min_length=1, max_length=120)
    area_sqm: float | None = Field(None, gt=0)
    bedrooms: int | None = Field(None, ge=0, le=20)
    price: int | None = Field(None, ge=0)
    availability: Availability = "available"
    delivery_date: date | None = None
    payment_plan: str | None = None
    description: str | None = None
    readiness: Readiness | None = None
    source_name: str | None = Field(None, max_length=120)
    source_updated_at: date | None = None
    source_version: str | None = Field(None, max_length=40)

    _c = field_validator("payment_plan", "description", "source_name", "source_version", mode="before")(_clean)


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=160)
    property_type: PropertyType | None = None
    location: str | None = Field(None, min_length=1, max_length=120)
    area_sqm: float | None = Field(None, gt=0)
    bedrooms: int | None = Field(None, ge=0, le=20)
    price: int | None = Field(None, ge=0)
    availability: Availability | None = None
    delivery_date: date | None = None
    payment_plan: str | None = None
    description: str | None = None
    readiness: Readiness | None = None
    source_name: str | None = Field(None, max_length=120)
    source_updated_at: date | None = None
    source_version: str | None = Field(None, max_length=40)


class PropertyOut(ORM):
    id: int
    code: str
    title: str
    property_type: str
    location: str
    area_sqm: float | None
    bedrooms: int | None
    price: int | None
    availability: str
    delivery_date: str | None
    payment_plan: str | None
    description: str | None
    readiness: str | None
    source_name: str | None
    source_updated_at: str | None
    source_version: str | None


class ActivityCreate(BaseModel):
    type: Literal["note", "call_log", "meeting_note"] = "note"
    description: str = Field(..., min_length=1, max_length=2000)


class ActivityOut(ORM):
    id: int
    lead_id: int | None
    handoff_id: int | None
    type: str
    description: str
    actor: str
    created_at: datetime


class BookingCreate(BaseModel):
    lead_id: int
    property_id: int
    start: datetime


class BookingCancel(BaseModel):
    reason: str | None = Field(None, max_length=200)


class BookingOut(BaseModel):
    id: int
    lead_id: int
    lead_name: str
    property_id: int
    property_title: str
    start: datetime
    end: datetime
    status: str
    simulated: bool = True
    label: str = "Simulated booking - no real appointment, message or calendar entry is created"
    cancel_reason: str | None = None
    created_at: datetime


class Slot(BaseModel):
    start: datetime
    end: datetime
    available: bool
    reason: str | None = None


class HandoffCreate(BaseModel):
    lead_id: int | None = None
    category: HandoffCategory
    reason: str = Field(..., min_length=3, max_length=2000)


class HandoffUpdate(BaseModel):
    status: HandoffStatus | None = None
    assigned_to: str | None = Field(None, max_length=80)
    note: str | None = Field(None, max_length=2000)


class HandoffOut(BaseModel):
    id: int
    lead_id: int | None
    lead_name: str | None
    category: str
    reason: str
    status: str
    assigned_to: str | None
    created_at: datetime
    updated_at: datetime
    events: list[ActivityOut] = []


class FollowUpSuggestion(BaseModel):
    kind: str
    text: str
    reason: str


class FollowUpOut(BaseModel):
    lead_id: int
    consent_status: str
    sendable: bool = False
    note: str = "Suggestions only. Nothing is sent by this application."
    warning: str | None = None
    suggestions: list[FollowUpSuggestion]


class CrmOut(BaseModel):
    lead: LeadOut
    qualification_complete: bool
    missing_qualification: list[str]
    activities: list[ActivityOut]
    bookings: list[BookingOut]
    handoffs: list[HandoffOut]
    open_handoff_status: str | None


class Citation(BaseModel):
    source: str
    text: str


class ConversationCreate(BaseModel):
    lead_id: int
    channel: LeadChannel = "whatsapp_sandbox"


class ChatMessageIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


class ChatMessageOut(BaseModel):
    id: int
    role: str
    text: str
    citations: list[Citation] = []
    module_gaps: list[str] = []
    created_at: datetime


class ConversationOut(BaseModel):
    id: int
    lead_id: int
    channel: str
    created_at: datetime
    messages: list[ChatMessageOut]
    lead: LeadOut


class DiscountBandIn(BaseModel):
    version: str = Field(..., min_length=1, max_length=40)
    min_pct: float = Field(0, ge=0, le=100)
    max_pct: float = Field(..., ge=0, le=100)
    notes: str | None = None
    active: bool = True


class DiscountBandOut(ORM):
    id: int
    version: str
    min_pct: float
    max_pct: float
    notes: str | None
    active: bool
    created_at: datetime
