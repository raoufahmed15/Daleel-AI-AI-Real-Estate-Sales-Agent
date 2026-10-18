"""Deterministic SYNTHETIC demo data. Usage: python -m app.seed [--reset]"""
import random
import sys
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from .models import Activity, Booking, Handoff, Lead, Property, utcnow

FIRST = ["Ahmed", "Mona", "Omar", "Salma", "Youssef", "Nour", "Karim", "Laila", "Hassan", "Dina", "Tarek", "Heba",
         "أحمد", "منى", "عمر", "سلمى", "يوسف", "نور", "كريم", "ليلى"]
LAST = ["Samir", "Adel", "Mansour", "Fathy", "Hegazy", "Zaki", "Nabil", "Farouk", "سمير", "عادل", "منصور", "فتحي"]
LOCATIONS = {"New Cairo": 55000, "Sheikh Zayed": 50000, "New Capital": 40000, "6th October": 32000,
             "North Coast": 60000, "Maadi": 65000}
TYPES = {"apartment": (70, 200, (1, 4)), "villa": (250, 500, (3, 6)), "townhouse": (180, 300, (3, 4)),
         "duplex": (160, 280, (3, 5)), "studio": (40, 70, (0, 1)), "penthouse": (200, 350, (3, 5)),
         "chalet": (60, 140, (1, 3)), "office": (50, 200, (0, 0))}
PLANS = ["10% down payment, 8-year installments", "15% down payment, 6-year installments",
         "5% down payment, 10-year installments", "Cash discount plan (synthetic)"]
TIMELINES = ["immediate", "1_3_months", "3_6_months", "6_12_months", "over_12_months"]
STATUSES = ["new"] * 8 + ["contacted"] * 7 + ["qualified"] * 6 + ["viewing_scheduled"] * 4 + ["negotiation"] * 3 + ["won", "lost"]


def seed_database(db: Session, today: date | None = None, n_leads=30, n_props=40, rng_seed=42):
    rng = random.Random(rng_seed)
    today = today or utcnow().date()
    base = datetime.combine(today, time(9)) - timedelta(days=30)

    props = []
    for i in range(1, n_props + 1):
        t = rng.choice(list(TYPES))
        lo, hi, (b0, b1) = TYPES[t]
        loc = rng.choice(list(LOCATIONS))
        area = float(rng.randrange(lo, hi + 1, 5))
        price = int(round(area * LOCATIONS[loc] * rng.uniform(0.9, 1.25), -4))
        p = Property(code=f"DLL-{i:04d}", title=f"{t.title()} in {loc}", property_type=t, location=loc,
                     area_sqm=area, bedrooms=rng.randint(b0, b1), price=price,
                     availability=rng.choices(["available", "reserved", "sold"], [70, 15, 15])[0],
                     delivery_date=(today + timedelta(days=rng.randrange(60, 1000, 30))).isoformat() if rng.random() < .7 else None,
                     payment_plan=rng.choice(PLANS) if rng.random() < .6 else None,
                     description="Synthetic demo unit." if rng.random() < .5 else None)
        props.append(p)
    db.add_all(props)

    leads = []
    for i in range(1, n_leads + 1):
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        opt = i in (7, 19, 26)
        lead = Lead(
            name=name, phone=f"+20 100 000 {i:04d}" if rng.random() < .9 else None,
            email=f"demo.lead{i}@example.com" if rng.random() < .7 else None,
            status=rng.choice(STATUSES), priority=rng.choices(["low", "medium", "high"], [25, 50, 25])[0],
            budget=rng.randrange(1_500_000, 12_000_000, 250_000) if rng.random() < .7 else None,
            preferred_location=rng.choice(list(LOCATIONS)) if rng.random() < .7 else None,
            property_type=rng.choice(list(TYPES)) if rng.random() < .7 else None,
            down_payment=None, monthly_installment=rng.randrange(10_000, 60_000, 5_000) if rng.random() < .5 else None,
            purchase_timeline=rng.choice(TIMELINES) if rng.random() < .6 else None,
            consent_status="denied" if i in (11,) else ("granted" if rng.random() < .7 else "unknown"),
            opted_out=opt, created_at=base + timedelta(days=rng.randint(0, 29), hours=rng.randint(0, 8)))
        if lead.budget and rng.random() < .7:
            lead.down_payment = int(lead.budget * rng.choice([0.1, 0.15, 0.2]) // 1000 * 1000)
        if opt:
            lead.consent_status = "denied"
        leads.append(lead)
    db.add_all(leads)
    db.flush()

    for l in leads:
        db.add(Activity(lead_id=l.id, type="lead_created", description=f"Lead '{l.name}' created (synthetic seed)",
                        actor="system", created_at=l.created_at))
        if l.status != "new":
            db.add(Activity(lead_id=l.id, type="stage_changed", description=f"Funnel stage: new -> {l.status}",
                            actor="system", created_at=l.created_at + timedelta(days=1)))
        if l.opted_out:
            db.add(Activity(lead_id=l.id, type="opt_out", description="Lead opted out of all follow-ups",
                            actor="system", created_at=l.created_at + timedelta(days=2)))

    # Bookings: 2 past, 6 upcoming, 2 cancelled (only for available properties / contactable leads)
    avail = [p for p in props if p.availability == "available"]
    contactable = [l for l in leads if not l.opted_out and l.consent_status != "denied"]
    plan = [(-5, "scheduled"), (-2, "scheduled")] + [(d, "scheduled") for d in (1, 1, 2, 3, 4, 6)] + [(2, "cancelled"), (5, "cancelled")]
    used = set()
    for k, (offset, status) in enumerate(plan):
        hour = 10 + (k % 6)
        start = datetime.combine(today + timedelta(days=offset), time(hour))
        lead, prop = contactable[k], avail[k]
        key = (start, prop.id)
        if key in used:
            continue
        used.add(key)
        b = Booking(lead_id=lead.id, property_id=prop.id, start=start, end=start + timedelta(hours=1), status=status,
                    cancel_reason="Lead asked to reschedule (synthetic)" if status == "cancelled" else None,
                    created_at=base + timedelta(days=25))
        db.add(b)
        db.add(Activity(lead_id=lead.id, type="booking_created", actor="system",
                        description=f"Simulated viewing booked: {prop.title} on {start:%Y-%m-%d %H:%M}"))
        if status == "cancelled":
            db.add(Activity(lead_id=lead.id, type="booking_cancelled", actor="system",
                            description=f"Simulated viewing cancelled: {prop.title} on {start:%Y-%m-%d %H:%M}"))

    cases = [("hot_lead", "Lead requests an urgent callback and mentions a ready cash payment.", "open", 0),
             ("complaint", "Lead complains about a missed callback.", "in_review", 1),
             ("discount_request", "Lead asks for a discount beyond standard terms.", "open", 2),
             ("conflicting_commercial_info", "Lead received two different delivery dates from different channels.", "open", 3),
             ("data_deletion_request", "Lead asks to delete all personal data.", "resolved", 6),
             ("legal_dispute", "Lead mentions a contract dispute with a previous developer.", "dismissed", 8)]
    for cat, reason, status, idx in cases:
        h = Handoff(lead_id=leads[idx].id, category=cat, reason=reason, status=status, assigned_to="Demo Reviewer" if status != "open" else None)
        db.add(h)
        db.flush()
        db.add(Activity(lead_id=h.lead_id, handoff_id=h.id, type="handoff_created",
                        description=f"Handoff #{h.id} ({cat}): {reason}", actor="system"))
    db.commit()


def reset_and_seed(db: Session):
    for model in (Activity, Booking, Handoff, Lead, Property):
        db.query(model).delete()
    db.commit()
    seed_database(db)


if __name__ == "__main__":
    from .database import init_db, make_engine, make_session_factory
    from . import config
    eng = make_engine(config.DATABASE_URL)
    init_db(eng)
    with make_session_factory(eng)() as session:
        if "--reset" in sys.argv:
            reset_and_seed(session)
            print("Database reset and seeded (synthetic data).")
        elif session.query(Lead).count():
            print("Database already has data. Use --reset to re-seed.")
        else:
            seed_database(session)
            print("Database seeded (synthetic data).")
