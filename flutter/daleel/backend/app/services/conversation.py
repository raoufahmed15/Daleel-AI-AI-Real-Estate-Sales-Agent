"""Sandbox sales conversation.

Rules engine always runs (identity, opt-out, qualification, guardrails, inventory cites).
RAG / recommendation ranking / scoring / LLM / STT / TTS / OCR stay empty until registered.
Commercial facts are never invented from the LLM slot.
"""
from __future__ import annotations

import json
import re
from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..integrations.contracts import (
    LlmAgentRequest, ModuleNotConfigured, RagRequest, RecommendationRequest, ChatTurn,
)
from ..errors import AppError
from ..models import Conversation, DiscountBand, Lead, Message, Property
from ..schemas import ChatMessageOut, Citation, ConversationOut, HandoffCreate, LeadOut
from .common import get_lead, log_activity
from .handoffs import create as create_handoff
from .leads import missing_qualification

IDENTITY = (
    "I'm Daleel, an AI sales assistant in a sandbox. "
    "I do not send real WhatsApp messages, place calls, or write to a production CRM."
)
WELCOME = (
    f"{IDENTITY} Tell me the unit type, area, budget, down payment, monthly installment, "
    "timeline and whether this is to live in or invest. I only record what you actually say."
)

OPT_OUT_MARKERS = ("stop", "unsubscribe", "opt out", "opt-out", "optout", "لا تتواصل", "وقف الرسائل", "إلغاء المتابعة")
COMPLAINT_MARKERS = ("complaint", "شكوى", "قاضي", "محامي", "lawyer", "attorney", "sue")
DELETE_MARKERS = ("delete my data", "احذف بياناتي", "امسح بياناتي")
DISCOUNT_MARKERS = ("discount", "خصم", "تخفيض")
MATCH_MARKERS = ("recommend", "suggest", "match", "units", "وحدات", "رشح", "ناسب")
COMMERCIAL_MARKERS = (
    "price", "سعر", "قسط", "installment", "available", "availability", "متاح", "توفر",
    "payment", "سداد", "delivery", "تسليم", "خطة",
)
TYPE_ALIASES = {
    "apartment": ("apartment", "flat", "شقة"),
    "villa": ("villa", "فيلا"),
    "townhouse": ("townhouse", "تاون"),
    "duplex": ("duplex", "دوبلكس"),
    "studio": ("studio", "استوديو"),
    "penthouse": ("penthouse", "بنتهاوس"),
    "chalet": ("chalet", "شاليه"),
    "office": ("office", "مكتب"),
}
TIMELINE_ALIASES = {
    "immediate": ("immediate", "now", "فوري", "دلوقتي"),
    "1_3_months": ("1-3", "1 to 3", "شهرين", "1_3"),
    "3_6_months": ("3-6", "3 to 6", "3_6"),
    "6_12_months": ("6-12", "6 to 12", "6_12"),
    "over_12_months": ("over 12", "more than 12", "سنة", "over_12"),
}

CODE_RE = re.compile(r"\bDLL-\d{4}\b", re.I)
NUMBER_RE = re.compile(r"(\d[\d,\.]*)\s*(m|mn|million|مليون)?", re.I)


def _json_list(raw: str | None) -> list:
    if not raw:
        return []
    return json.loads(raw)


def _msg_out(m: Message) -> ChatMessageOut:
    return ChatMessageOut(
        id=m.id, role=m.role, text=m.text, created_at=m.created_at,
        citations=[Citation(**c) for c in _json_list(m.citations_json)],
        module_gaps=_json_list(m.module_gaps_json),
    )


def _out(conv: Conversation) -> ConversationOut:
    return ConversationOut(
        id=conv.id, lead_id=conv.lead_id, channel=conv.channel, created_at=conv.created_at,
        messages=[_msg_out(m) for m in conv.messages],
        lead=LeadOut.model_validate(conv.lead),
    )


def _add(db: Session, conv: Conversation, role: str, text: str, citations=None, gaps=None) -> Message:
    m = Message(
        conversation_id=conv.id, role=role, text=text,
        citations_json=json.dumps(citations or [], ensure_ascii=False) if citations else None,
        module_gaps_json=json.dumps(gaps or [], ensure_ascii=False) if gaps else None,
    )
    db.add(m)
    db.flush()
    return m


def list_for_lead(db: Session, lead_id: int) -> list[Conversation]:
    get_lead(db, lead_id)
    return db.scalars(select(Conversation).where(Conversation.lead_id == lead_id).order_by(Conversation.id.desc())).all()


def get_conversation(db: Session, conversation_id: int) -> Conversation:
    conv = db.get(Conversation, conversation_id)
    if not conv:
        from ..errors import not_found
        raise not_found("Conversation", conversation_id)
    return conv


def open_conversation(db: Session, lead_id: int, channel: str, registry) -> Conversation:
    lead = get_lead(db, lead_id)
    existing = db.scalars(
        select(Conversation).where(Conversation.lead_id == lead.id, Conversation.channel == channel)
        .order_by(Conversation.id.desc())
    ).first()
    if existing:
        return existing
    if lead.opted_out:
        raise AppError(409, "lead_opted_out", "This lead opted out. No new conversation can be started.")
    conv = Conversation(lead_id=lead.id, channel=channel)
    db.add(conv)
    db.flush()
    _add(db, conv, "system", IDENTITY)
    _add(db, conv, "assistant", WELCOME, gaps=_empty_slots(registry))
    log_activity(db, lead.id, "conversation_opened", f"Sandbox {channel} conversation #{conv.id} opened", actor="agent")
    db.commit()
    db.refresh(conv)
    return conv


def _empty_slots(registry) -> list[str]:
    from ..integrations.contracts import MODULES
    return [name for name in MODULES if registry.status(name) != "integrated"]


def _call(registry, name, payload):
    handler = registry.get(name)
    if handler is None:
        return None, "not_implemented"
    try:
        from ..integrations.contracts import MODULES
        result = handler(payload)
        return MODULES[name]["response"].model_validate(result), "ok"
    except ModuleNotConfigured:
        return None, "not_configured"


def _active_band(db: Session) -> DiscountBand | None:
    return db.scalars(select(DiscountBand).where(DiscountBand.active.is_(True)).order_by(DiscountBand.id.desc())).first()


def _extract_updates(lead: Lead, text: str, db: Session) -> dict:
    low = text.lower()
    updates = {}
    if lead.property_type is None:
        for key, aliases in TYPE_ALIASES.items():
            if any(a in low for a in aliases):
                updates["property_type"] = key
                break
    if lead.purchase_purpose is None:
        if any(w in low for w in ("invest", "استثمار", "investment")):
            updates["purchase_purpose"] = "invest"
        elif any(w in low for w in ("live", "سكن", "أسكن", "living")):
            updates["purchase_purpose"] = "live"
    if lead.purchase_timeline is None:
        for key, aliases in TIMELINE_ALIASES.items():
            if any(a in low for a in aliases):
                updates["purchase_timeline"] = key
                break
    if lead.preferred_location is None:
        locs = db.scalars(select(Property.location).distinct()).all()
        for loc in locs:
            if loc and loc.lower() in low:
                updates["preferred_location"] = loc
                break
    nums = NUMBER_RE.findall(text.replace(",", ""))
    parsed = []
    for raw, unit in nums:
        try:
            n = float(raw)
        except ValueError:
            continue
        if unit:
            n *= 1_000_000
        parsed.append(int(n))
    if parsed and lead.budget is None and max(parsed) >= 200_000:
        updates["budget"] = max(parsed)
    mids = [n for n in parsed if 5_000 <= n <= 150_000]
    if mids and lead.monthly_installment is None:
        updates["monthly_installment"] = mids[0]
    downs = [n for n in parsed if 50_000 <= n < (updates.get("budget") or lead.budget or 10**12)]
    if downs and lead.down_payment is None and ("down" in low or "مقدم" in text):
        updates["down_payment"] = downs[0]
    return updates


def _ask_next(lead: Lead) -> str | None:
    missing = missing_qualification(lead)
    prompts = {
        "budget": "What budget range are you working with (EGP)? Leave it blank if you have not decided.",
        "preferred_location": "Which area are you looking at?",
        "property_type": "What unit type (apartment, villa, townhouse, …)?",
        "down_payment": "What down payment can you put down? I will not guess.",
        "monthly_installment": "What monthly installment is comfortable?",
        "purchase_timeline": "When do you want to buy (immediate, 1-3 months, …)?",
        "purchase_purpose": "Is this to live in, or an investment?",
    }
    if not missing:
        return None
    return prompts[missing[0]]


def _inventory_cite(p: Property) -> tuple[str, list[dict], bool]:
    if not p.source_name or not p.source_updated_at or not p.source_version:
        return (
            f"Unit {p.code} is in inventory but has no trusted source/date/version, so I will not quote a commercial figure. "
            "A sales reviewer must confirm.",
            [],
            True,
        )
    try:
        source_date = date.fromisoformat(p.source_updated_at)
    except ValueError:
        return (
            f"Unit {p.code} has an invalid source date, so I will not quote a commercial figure. "
            "A sales reviewer must confirm.",
            [],
            True,
        )
    if source_date > date.today():
        return (
            f"Unit {p.code} has a future source date, so I will not quote a commercial figure. "
            "A sales reviewer must confirm.",
            [],
            True,
        )
    bits = [f"Unit {p.code} ({p.title})."]
    cites = []
    src = f"{p.source_name} · {p.source_updated_at} · {p.source_version}"
    if p.price is not None:
        bits.append(f"Listed price: {p.price:,} EGP.")
        cites.append({"source": src, "text": f"{p.code} price {p.price}"})
    else:
        bits.append("Price is not recorded. I will not invent it.")
    if p.availability:
        bits.append(f"Availability: {p.availability}.")
        cites.append({"source": src, "text": f"{p.code} availability {p.availability}"})
    if p.payment_plan:
        bits.append(f"Payment plan: {p.payment_plan}.")
        cites.append({"source": src, "text": p.payment_plan})
    if p.delivery_date:
        bits.append(f"Delivery date: {p.delivery_date}.")
        cites.append({"source": src, "text": f"delivery {p.delivery_date}"})
    if p.readiness:
        bits.append(f"Readiness: {p.readiness}.")
    return " ".join(bits), cites, False


def _hard_filter(db: Session, lead: Lead, limit=5) -> list[Property]:
    stmt = select(Property).where(Property.availability == "available")
    if lead.property_type:
        stmt = stmt.where(Property.property_type == lead.property_type)
    if lead.preferred_location:
        stmt = stmt.where(Property.location.ilike(f"%{lead.preferred_location}%"))
    if lead.budget is not None:
        stmt = stmt.where((Property.price.is_(None)) | (Property.price <= lead.budget))
    return db.scalars(stmt.order_by(Property.id.asc()).limit(limit)).all()


def post_message(db: Session, conversation_id: int, text: str, registry) -> Conversation:
    conv = get_conversation(db, conversation_id)
    lead = conv.lead
    if lead.opted_out:
        raise AppError(409, "lead_opted_out", "This lead opted out. No further chat messages are allowed.")
    _add(db, conv, "user", text.strip())
    reply, citations, gaps, actions = _decide(db, conv, lead, text.strip(), registry)
    _add(db, conv, "assistant", reply, citations=citations, gaps=gaps)
    for kind, desc in actions:
        log_activity(db, lead.id, kind, desc, actor="agent")
    lead.conversation_summary = reply[:500]
    db.commit()
    db.refresh(conv)
    return conv


def _decide(db: Session, conv: Conversation, lead: Lead, text: str, registry):
    citations: list[dict] = []
    gaps: list[str] = []
    actions: list[tuple[str, str]] = []
    low = text.lower()

    if any(m in low for m in OPT_OUT_MARKERS):
        lead.opted_out = True
        lead.consent_status = "denied"
        actions.append(("opt_out", "Lead opted out from sandbox chat. No further follow-up suggestions will be created."))
        return "Opt-out recorded. I will not create any further follow-up or booking suggestions.", citations, gaps, actions

    if any(m in low for m in DELETE_MARKERS):
        h = create_handoff(db, HandoffCreate(
            lead_id=lead.id, category="data_deletion_request",
            reason="Lead asked to delete personal data from sandbox chat.",
        ))
        actions.append(("handoff_created", f"Handoff #{h.id} data_deletion_request"))
        return "That is a data-deletion request. I opened a human handoff and will not keep selling.", citations, gaps, actions

    if any(m in low for m in COMPLAINT_MARKERS):
        h = create_handoff(db, HandoffCreate(
            lead_id=lead.id, category="complaint",
            reason=f"Complaint/legal language in sandbox chat: {text[:240]}",
        ))
        actions.append(("handoff_created", f"Handoff #{h.id} complaint"))
        return "I am transferring this to a human reviewer (complaint / legal). I will not continue a commercial pitch.", citations, gaps, actions

    if any(m in low for m in DISCOUNT_MARKERS):
        band = _active_band(db)
        nums = [int(float(n.replace(",", ""))) for n, _ in NUMBER_RE.findall(text.replace(",", "")) if n]
        pct = next((n for n in nums if 0 < n <= 100), None)
        if band is None:
            h = create_handoff(db, HandoffCreate(
                lead_id=lead.id, category="discount_request",
                reason="Discount asked but no active versioned discount band is configured.",
            ))
            actions.append(("handoff_created", f"Handoff #{h.id} discount_request"))
            return "I do not negotiate discounts outside owner-entered bands. None are active, so this is a human handoff.", citations, gaps, actions
        if pct is not None and pct > band.max_pct:
            h = create_handoff(db, HandoffCreate(
                lead_id=lead.id, category="discount_request",
                reason=f"Requested {pct}% which is outside band {band.version} (max {band.max_pct}%).",
            ))
            actions.append(("handoff_created", f"Handoff #{h.id} discount_request"))
            return (
                f"Requested discount is outside versioned band {band.version} "
                f"({band.min_pct}–{band.max_pct}%). I will not promise it. Human handoff opened."
            ), citations, gaps, actions
        return (
            f"I can only stay inside discount band {band.version} ({band.min_pct}–{band.max_pct}%). "
            "I will not invent a better offer."
        ), citations, gaps, actions

    updates = _extract_updates(lead, text, db)
    if updates:
        for k, v in updates.items():
            setattr(lead, k, v)
        actions.append(("qualification_updated", "Captured from chat: " + ", ".join(updates)))

    code_hit = CODE_RE.search(text)
    if code_hit or any(m in low for m in COMMERCIAL_MARKERS):
        rag_body, rag_st = _call(registry, "rag", RagRequest(question=text, lead_id=lead.id))
        if rag_st == "ok" and rag_body is not None:
            body = rag_body.model_dump()
            verified_evidence = [
                ev for ev in body.get("evidence", [])
                if ev.get("source_updated_at")
                and ev["source_updated_at"] <= date.today()
                and ev.get("source_version")
            ]
            if verified_evidence and body.get("answer"):
                citations = [
                    {
                        "source": f"{ev['source']} · {ev['source_updated_at']} · {ev['source_version']}",
                        "text": ev["text"][:240],
                    }
                    for ev in verified_evidence
                ]
                return body["answer"], citations, gaps, actions
        gaps.append("rag")
        if code_hit:
            p = db.scalars(select(Property).where(Property.code == code_hit.group(0).upper())).first()
            if p:
                msg, cites, needs_handoff = _inventory_cite(p)
                if needs_handoff:
                    h = create_handoff(db, HandoffCreate(
                        lead_id=lead.id, category="conflicting_commercial_info",
                        reason=f"{p.code} is missing a trusted source/date for a commercial answer.",
                    ))
                    actions.append(("handoff_created", f"Handoff #{h.id} conflicting_commercial_info"))
                return msg, cites, gaps, actions
        return (
            "Price, availability and payment plans only come from a trusted inventory row (with source + date) "
            "or from your RAG knowledge base with a source, update date and version. "
            "RAG is not connected or did not return verifiable citations, and I did not find a unit code such as DLL-0001. "
            "I will not invent a figure."
        ), citations, gaps, actions

    if any(m in low for m in MATCH_MARKERS) or (not missing_qualification(lead) and "unit" in low):
        rec_body, rec_st = _call(registry, "recommendation_engine", RecommendationRequest(
            lead_id=lead.id, budget=lead.budget, preferred_location=lead.preferred_location,
            property_type=lead.property_type, limit=3,
        ))
        if rec_st == "ok" and rec_body is not None:
            body = rec_body if isinstance(rec_body, dict) else rec_body.model_dump()
            lines = [f"#{it.get('rank')} property {it.get('property_id')}: {it.get('explanation')}" for it in body.get("items", [])]
            return "Ranked matches from your recommendation engine:\n" + ("\n".join(lines) or "(empty)"), citations, gaps, actions
        gaps.append("recommendation_engine")
        found = _hard_filter(db, lead)
        if not found:
            return (
                "Hard-filter on stored inventory returned no available units for the known constraints. "
                "The ranking engine is not connected, so I will not invent alternatives."
            ), citations, gaps, actions
        lines = [f"{p.code} · {p.title} · {p.location}" + (f" · {p.price:,} EGP" if p.price is not None else " · price not recorded")
                 for p in found]
        return (
            "Hard-filter matches from inventory only (ranking engine not connected — order is not a learned rank):\n"
            + "\n".join(lines)
        ), citations, gaps, actions

    ask = _ask_next(lead)
    if ask:
        prefix = "Noted. " if updates else ""
        return prefix + ask, citations, gaps, actions

    llm_body, llm_st = _call(registry, "llm_agent", LlmAgentRequest(
        lead_id=lead.id,
        messages=[ChatTurn(role=m.role, text=m.text) for m in conv.messages] + [ChatTurn(role="user", text=text)],
    ))
    if llm_st == "ok" and llm_body is not None:
        body = llm_body if isinstance(llm_body, dict) else llm_body.model_dump()
        return body.get("reply") or IDENTITY, citations, gaps, actions
    gaps.append("llm_agent")
    return (
        f"{IDENTITY} Qualification looks complete on stored fields. "
        "I can hard-filter inventory if you ask for matching units, or you can book a simulated viewing. "
        "I will not promise returns, fake urgency, or a discount outside the versioned bands. "
        "The local LLM slot is empty, so I am staying on the sandbox rules engine."
    ), citations, gaps, actions
