from sqlalchemy import func, select

from app.main import create_app
from app.models import Lead, Property
from app.seed import seed_database
from fastapi.testclient import TestClient
from .conftest import mk_lead, mk_prop, tomorrow_at


# ---- DB init & seeding -------------------------------------------------------
def test_db_initialization_creates_empty_tables(app):
    with app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Lead)) == 0
        assert db.scalar(select(func.count()).select_from(Property)) == 0


def test_seed_is_deterministic():
    snapshots = []
    for _ in range(2):
        a = create_app("sqlite://", auto_seed=False)
        with a.state.session_factory() as db:
            seed_database(db)
            leads = [(l.name, l.budget, l.status) for l in db.scalars(select(Lead).order_by(Lead.id))]
            props = [(p.code, p.price, p.availability) for p in db.scalars(select(Property).order_by(Property.id))]
        snapshots.append((leads, props))
    assert snapshots[0] == snapshots[1]
    assert len(snapshots[0][0]) == 30 and len(snapshots[0][1]) == 40


def test_seed_does_not_fabricate_missing_values(seeded):
    props = seeded.get("/api/properties?limit=200").json()["items"]
    assert any(p["delivery_date"] is None for p in props)
    assert any(p["payment_plan"] is None for p in props)
    leads = seeded.get("/api/leads?limit=200").json()["items"]
    assert any(l["budget"] is None for l in leads)


# ---- Health / errors ---------------------------------------------------------
def test_health_and_docs(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/docs").status_code == 200


def test_error_envelope(client):
    r = client.get("/api/leads/999")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    r = client.post("/api/leads", json={"name": ""})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


# ---- Leads -------------------------------------------------------------------
def test_lead_create_get_update_delete(client):
    lead = mk_lead(client, name="  Sara  ", budget=3_000_000)
    assert lead["name"] == "Sara" and lead["consent_status"] == "unknown" and lead["opted_out"] is False
    assert client.get(f"/api/leads/{lead['id']}").json()["budget"] == 3_000_000
    r = client.patch(f"/api/leads/{lead['id']}", json={"priority": "high", "next_steps": "Call Sunday"})
    assert r.json()["priority"] == "high" and r.json()["next_steps"] == "Call Sunday"
    assert client.delete(f"/api/leads/{lead['id']}").status_code == 204
    assert client.get(f"/api/leads/{lead['id']}").status_code == 404


def test_lead_validation(client):
    assert client.post("/api/leads", json={"name": "A", "email": "nope"}).status_code == 422
    assert client.post("/api/leads", json={"name": "A", "phone": "abc"}).status_code == 422
    assert client.post("/api/leads", json={"name": "A", "budget": -1}).status_code == 422
    assert client.post("/api/leads", json={"name": "A", "status": "bogus"}).status_code == 422
    r = client.post("/api/leads", json={"name": "A", "budget": 1000, "down_payment": 2000})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_lead_search_filter_pagination(seeded):
    all_ = seeded.get("/api/leads?limit=10").json()
    assert all_["total"] == 30 and len(all_["items"]) == 10
    name = all_["items"][0]["name"].split()[0]
    hits = seeded.get(f"/api/leads?q={name}&limit=200").json()
    assert hits["total"] >= 1 and all(name.lower() in i["name"].lower() for i in hits["items"] if not i["email"])
    assert seeded.get("/api/leads?q=zzzz-no-match").json()["total"] == 0
    st = seeded.get("/api/leads?status=new&limit=200").json()
    assert all(i["status"] == "new" for i in st["items"])


def test_qualification_update_keeps_unknown_as_null(client):
    lead = mk_lead(client)
    r = client.put(f"/api/leads/{lead['id']}/qualification",
                   json={"budget": 4_000_000, "preferred_location": "New Cairo", "purchase_timeline": "1_3_months"})
    assert r.status_code == 200
    body = r.json()
    assert body["budget"] == 4_000_000 and body["down_payment"] is None and body["property_type"] is None
    crm = client.get(f"/api/leads/{lead['id']}/crm").json()
    assert crm["qualification_complete"] is False and "down_payment" in crm["missing_qualification"]


# ---- Properties --------------------------------------------------------------
def test_property_crud(client):
    p = mk_prop(client, delivery_date="2028-01-01", payment_plan="10% down")
    assert p["code"].startswith("DLL-") and p["delivery_date"] == "2028-01-01"
    r = client.patch(f"/api/properties/{p['id']}", json={"price": 5_500_000, "availability": "reserved"})
    assert r.json()["price"] == 5_500_000 and r.json()["availability"] == "reserved"
    assert client.delete(f"/api/properties/{p['id']}").status_code == 204
    assert client.get(f"/api/properties/{p['id']}").status_code == 404


def test_property_unknown_fields_stay_null(client):
    r = client.post("/api/properties", json={"title": "Bare", "property_type": "villa", "location": "Maadi"})
    p = r.json()
    assert p["price"] is None and p["delivery_date"] is None and p["payment_plan"] is None


def test_property_validation_and_duplicate_code(client):
    assert client.post("/api/properties", json={"title": "x", "property_type": "castle", "location": "y"}).status_code == 422
    assert client.post("/api/properties", json={"title": "x", "property_type": "villa", "location": "y", "area_sqm": 0}).status_code == 422
    mk_prop(client, code="ABC-1")
    r = client.post("/api/properties", json={"title": "x", "property_type": "villa", "location": "y", "code": "ABC-1"})
    assert r.status_code == 409


def test_property_search_and_filters(client):
    mk_prop(client, title="A", price=2_000_000, bedrooms=1, area_sqm=60, location="Maadi")
    mk_prop(client, title="B", price=6_000_000, bedrooms=3, area_sqm=150, location="New Cairo", property_type="villa")
    mk_prop(client, title="C", price=9_000_000, bedrooms=5, area_sqm=300, location="New Cairo", availability="sold")
    g = lambda qs: client.get(f"/api/properties?{qs}").json()
    assert g("location=maadi")["total"] == 1
    assert g("min_price=5000000&max_price=7000000")["items"][0]["title"] == "B"
    assert g("property_type=villa")["total"] == 1
    assert g("min_bedrooms=3")["total"] == 2
    assert g("availability=sold")["items"][0]["title"] == "C"
    assert g("min_area=100&max_area=200")["total"] == 1
    assert [i["title"] for i in g("sort=price_desc")["items"]] == ["C", "B", "A"]
    assert g("q=B")["total"] >= 1


def test_property_with_booking_cannot_be_deleted(client):
    lead, prop = mk_lead(client), mk_prop(client)
    b = client.post("/api/bookings", json={"lead_id": lead["id"], "property_id": prop["id"], "start": tomorrow_at()})
    assert b.status_code == 201
    assert client.delete(f"/api/properties/{prop['id']}").status_code == 409


# ---- CRM activity log --------------------------------------------------------
def test_crm_activity_logging(client):
    lead = mk_lead(client)
    lid = lead["id"]
    client.patch(f"/api/leads/{lid}", json={"status": "contacted"})
    client.put(f"/api/leads/{lid}/qualification", json={"budget": 1_000_000})
    client.post(f"/api/leads/{lid}/activities", json={"type": "note", "description": "Spoke by phone"})
    client.put(f"/api/leads/{lid}/consent", json={"consent_status": "granted"})
    types = [a["type"] for a in client.get(f"/api/leads/{lid}/activities").json()]
    for t in ("lead_created", "stage_changed", "qualification_updated", "note", "consent_changed"):
        assert t in types
    assert client.post(f"/api/leads/{lid}/activities", json={"description": ""}).status_code == 422
    assert client.get("/api/leads/999/activities").status_code == 404


# ---- Bookings ----------------------------------------------------------------
def test_booking_create_cancel_and_history(client):
    lead, prop = mk_lead(client), mk_prop(client)
    r = client.post("/api/bookings", json={"lead_id": lead["id"], "property_id": prop["id"], "start": tomorrow_at(11)})
    assert r.status_code == 201
    b = r.json()
    assert b["simulated"] is True and "Simulated" in b["label"] and b["status"] == "scheduled"
    assert client.get(f"/api/leads/{lead['id']}").json()["status"] == "viewing_scheduled"
    c = client.post(f"/api/bookings/{b['id']}/cancel", json={"reason": "changed mind"})
    assert c.json()["status"] == "cancelled" and c.json()["cancel_reason"] == "changed mind"
    assert client.post(f"/api/bookings/{b['id']}/cancel").status_code == 409
    hist = client.get(f"/api/bookings?lead_id={lead['id']}").json()
    assert len(hist) == 1 and hist[0]["status"] == "cancelled"
    types = [a["type"] for a in client.get(f"/api/leads/{lead['id']}/activities").json()]
    assert "booking_created" in types and "booking_cancelled" in types


def test_booking_conflict_detection(client):
    l1, l2 = mk_lead(client, name="L1"), mk_lead(client, name="L2")
    p1, p2 = mk_prop(client, title="P1"), mk_prop(client, title="P2")
    ok = lambda l, p, h: client.post("/api/bookings", json={"lead_id": l["id"], "property_id": p["id"], "start": tomorrow_at(h)})
    assert ok(l1, p1, 10).status_code == 201
    r = ok(l2, p1, 10)  # same property, same slot
    assert r.status_code == 409 and r.json()["error"]["code"] == "booking_conflict"
    r = ok(l1, p2, 10)  # same lead, same slot
    assert r.status_code == 409 and r.json()["error"]["code"] == "booking_conflict"
    assert ok(l2, p2, 10).status_code == 201  # different lead + property is fine
    # cancelled slot is freed
    b = next(x for x in client.get("/api/bookings").json() if x["lead_id"] == l1["id"])
    client.post(f"/api/bookings/{b['id']}/cancel")
    l3 = mk_lead(client, name="L3")
    assert ok(l3, p1, 10).status_code == 201  # slot freed by the cancellation


def test_booking_slots_reflect_conflicts(client):
    lead, prop = mk_lead(client), mk_prop(client)
    start = tomorrow_at(12)
    client.post("/api/bookings", json={"lead_id": lead["id"], "property_id": prop["id"], "start": start})
    day = start[:10]
    slots = client.get(f"/api/bookings/slots?property_id={prop['id']}&day={day}").json()
    by_hour = {s["start"][11:13]: s for s in slots}
    assert by_hour["12"]["available"] is False and by_hour["12"]["reason"] == "property_booked"
    assert by_hour["10"]["available"] is True


def test_booking_rules(client):
    lead = mk_lead(client)
    sold = mk_prop(client, availability="sold")
    prop = mk_prop(client)
    post = lambda **kw: client.post("/api/bookings", json={"lead_id": lead["id"], "property_id": prop["id"], "start": tomorrow_at(), **kw})
    assert client.post("/api/bookings", json={"lead_id": lead["id"], "property_id": sold["id"], "start": tomorrow_at()}).status_code == 409
    assert post(start="2000-01-01T10:00:00").status_code == 422          # past
    assert post(start=tomorrow_at(22)).status_code == 422                 # outside hours
    assert client.post("/api/bookings", json={"lead_id": 999, "property_id": prop["id"], "start": tomorrow_at()}).status_code == 404
    assert client.post("/api/bookings", json={"lead_id": lead["id"], "property_id": 999, "start": tomorrow_at()}).status_code == 404


# ---- Consent / opt-out -------------------------------------------------------
def test_optout_blocks_followups_and_bookings(client):
    lead, prop = mk_lead(client), mk_prop(client)
    lid = lead["id"]
    assert client.get(f"/api/leads/{lid}/follow-ups").status_code == 200
    r = client.put(f"/api/leads/{lid}/consent", json={"opted_out": True})
    assert r.json()["opted_out"] is True
    f = client.get(f"/api/leads/{lid}/follow-ups")
    assert f.status_code == 409 and f.json()["error"]["code"] == "lead_opted_out"
    b = client.post("/api/bookings", json={"lead_id": lid, "property_id": prop["id"], "start": tomorrow_at()})
    assert b.status_code == 409 and b.json()["error"]["code"] == "lead_opted_out"
    assert "opt_out" in [a["type"] for a in client.get(f"/api/leads/{lid}/activities").json()]
    client.put(f"/api/leads/{lid}/consent", json={"opted_out": False})
    assert client.get(f"/api/leads/{lid}/follow-ups").status_code == 200


def test_consent_denied_blocks_followups(client):
    lead = mk_lead(client)
    client.put(f"/api/leads/{lead['id']}/consent", json={"consent_status": "denied"})
    r = client.get(f"/api/leads/{lead['id']}/follow-ups")
    assert r.status_code == 409 and r.json()["error"]["code"] == "consent_denied"
    assert client.put(f"/api/leads/{lead['id']}/consent", json={}).status_code == 422


def test_followups_are_suggestions_only(client):
    lead = mk_lead(client)
    f = client.get(f"/api/leads/{lead['id']}/follow-ups").json()
    assert f["sendable"] is False and "Nothing is sent" in f["note"]
    assert f["warning"] and any(s["kind"] == "collect_qualification" for s in f["suggestions"])


# ---- Handoffs ----------------------------------------------------------------
def test_handoff_lifecycle(client):
    lead = mk_lead(client)
    r = client.post("/api/handoffs", json={"lead_id": lead["id"], "category": "discount_request", "reason": "Wants 20% off"})
    assert r.status_code == 201
    h = r.json()
    assert h["status"] == "open" and h["lead_name"] == "Test Lead" and len(h["events"]) == 1
    u = client.patch(f"/api/handoffs/{h['id']}", json={"status": "in_review", "assigned_to": "Sara", "note": "Looking"}).json()
    assert u["status"] == "in_review" and u["assigned_to"] == "Sara" and len(u["events"]) >= 4
    assert client.patch(f"/api/handoffs/{h['id']}", json={"status": "in_review"}).status_code == 200  # no-op, same status
    assert client.patch(f"/api/handoffs/{h['id']}", json={"status": "resolved"}).json()["status"] == "resolved"
    bad = client.patch(f"/api/handoffs/{h['id']}", json={"status": "in_review"})
    assert bad.status_code == 409 and bad.json()["error"]["code"] == "invalid_transition"
    assert client.patch(f"/api/handoffs/{h['id']}", json={}).status_code == 422
    assert client.get("/api/handoffs?status=resolved").json()[0]["id"] == h["id"]
    assert "handoff_created" in [a["type"] for a in client.get(f"/api/leads/{lead['id']}/activities").json()]


def test_handoff_validation_and_all_categories(client):
    assert client.post("/api/handoffs", json={"category": "nope", "reason": "abc"}).status_code == 422
    assert client.post("/api/handoffs", json={"category": "other", "reason": "x"}).status_code == 422
    assert client.post("/api/handoffs", json={"category": "other", "reason": "abc", "lead_id": 999}).status_code == 404
    for cat in ("hot_lead", "complaint", "conflicting_commercial_info", "discount_request",
                "legal_dispute", "data_deletion_request", "other"):
        assert client.post("/api/handoffs", json={"category": cat, "reason": "needs review"}).status_code == 201


# ---- Discount guardrails -----------------------------------------------------
def test_discount_band_api_is_available_and_validates_ranges(client):
    assert client.get("/api/guardrails/discount-bands").json() == []
    created = client.post(
        "/api/guardrails/discount-bands",
        json={"version": "v1", "min_pct": 0, "max_pct": 5, "active": True},
    )
    assert created.status_code == 201
    band = created.json()
    updated = client.put(
        f"/api/guardrails/discount-bands/{band['id']}",
        json={"version": "v2", "min_pct": 1, "max_pct": 4, "active": True},
    )
    assert updated.status_code == 200 and updated.json()["version"] == "v2"
    invalid = client.post(
        "/api/guardrails/discount-bands",
        json={"version": "invalid", "min_pct": 8, "max_pct": 5},
    )
    assert invalid.status_code == 422


# ---- Dashboard ---------------------------------------------------------------
def test_dashboard_reflects_stored_data(client):
    d = lambda: client.get("/api/dashboard").json()
    assert d()["calculated"]["leads_total"] == 0
    lead, prop = mk_lead(client), mk_prop(client)
    mk_prop(client, availability="sold")
    client.post("/api/bookings", json={"lead_id": lead["id"], "property_id": prop["id"], "start": tomorrow_at()})
    client.post("/api/handoffs", json={"lead_id": lead["id"], "category": "complaint", "reason": "unhappy"})
    c = d()["calculated"]
    assert c["leads_total"] == 1 and c["leads_by_status"]["viewing_scheduled"] == 1
    assert c["properties_total"] == 2 and c["properties_available"] == 1
    assert c["bookings_upcoming"] == 1 and c["handoffs_pending"] == 1 and c["crm_activities_total"] >= 3
    assert {m["status"] for m in d()["unavailable_ai_metrics"]} == {"not_implemented"}


def test_dashboard_on_seed(seeded):
    c = seeded.get("/api/dashboard").json()["calculated"]
    assert c["leads_total"] == 30 and c["properties_total"] == 40
    assert sum(c["leads_by_status"].values()) == 30
    assert c["handoffs_pending"] == 4 and c["bookings_upcoming"] == 6 and c["bookings_cancelled"] == 2


# ---- Excluded modules --------------------------------------------------------
def test_excluded_modules_report_not_integrated(client):
    mods = client.get("/api/integrations").json()["modules"]
    assert {m["module"] for m in mods} == {
        "recommendation_engine", "lead_scoring", "rag", "stt", "tts", "ocr", "llm_agent"
    }
    assert all(m["status"] == "not_implemented" and m["label"] == "Not integrated yet"
               and m["integration_slot"] for m in mods)
    for url, body in (
        ("recommendation-engine/query", {"budget": 1}),
        ("lead-scoring/score", {"lead_id": 1}),
        ("rag/query", {"question": "What is the delivery date?"}),
        ("stt/transcribe", {"audio_ref": "local://clip.wav"}),
        ("tts/speak", {"text": "Test reply"}),
        ("ocr/extract", {"document_name": "brochure.pdf", "document_ref": "local://brochure.pdf"}),
        ("llm-agent/chat", {"messages": [{"role": "user", "text": "Hello"}]}),
    ):
        r = client.post(f"/api/integrations/{url}", json=body)
        assert r.status_code == 501 and r.json()["status"] == "not_implemented"
        assert "score" not in r.json() and "items" not in r.json() and "answer" not in r.json()
    assert client.post("/api/integrations/rag/query", json={"question": ""}).status_code == 422
    assert client.get("/api/settings").json()["external_ai_calls_enabled"] is False


def test_startup_is_empty_by_default_and_extension_hook_is_ready():
    a = create_app("sqlite://")
    c = TestClient(a)
    assert c.get("/api/health").json()["status"] == "ok"
    assert c.get("/api/leads").json()["total"] == 0
    assert c.get("/api/properties").json()["total"] == 0


def test_explicit_auto_seed_remains_opt_in():
    a = create_app("sqlite://", auto_seed=True)
    assert TestClient(a).get("/api/leads").json()["total"] == 30


def test_registry_contract_when_module_is_registered(app, client):
    from app.integrations.contracts import ModuleNotConfigured
    reg = app.state.registry
    reg.register("lead_scoring", lambda req: {"lead_id": req.lead_id, "score": 50.0, "explanations": ["test double"]})
    r = client.post("/api/integrations/lead-scoring/score", json={"lead_id": 1})
    assert r.status_code == 200 and r.json()["status"] == "integrated"
    assert any(m["status"] == "integrated" for m in client.get("/api/integrations").json()["modules"])

    def boom(_):
        raise ModuleNotConfigured("model path missing")
    reg.register("rag", boom)
    r = client.post("/api/integrations/rag/query", json={"question": "hi"})
    assert r.status_code == 503 and r.json()["status"] == "not_configured"
    try:
        reg.register("unknown", lambda r: r)
        assert False
    except KeyError:
        pass


def test_registered_modules_validate_responses(client, app):
    from app.integrations.contracts import ModuleNotConfigured

    app.state.registry.register(
        "stt",
        lambda request: {"transcript": "sample transcript", "confidence": 0.9},
    )
    response = client.post("/api/integrations/stt/transcribe", json={"audio_ref": "local://clip.wav"})
    assert response.status_code == 200
    assert response.json() == {
        "status": "integrated",
        "transcript": "sample transcript",
        "confidence": 0.9,
    }

    app.state.registry.register("ocr", lambda request: (_ for _ in ()).throw(
        ModuleNotConfigured("OCR model path is not configured")
    ))
    response = client.post(
        "/api/integrations/ocr/extract",
        json={"document_name": "brochure.pdf"},
    )
    assert response.status_code == 503
    assert response.json()["status"] == "not_configured"


def test_conversation_sandbox_records_opt_out_and_blocks_later_chat(client):
    lead = mk_lead(client)
    opened = client.post(
        "/api/conversations",
        json={"lead_id": lead["id"], "channel": "whatsapp_sandbox"},
    )
    assert opened.status_code == 201
    conversation = opened.json()
    assert "AI sales assistant" in conversation["messages"][-1]["text"]

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages",
        json={"text": "STOP"},
    )
    assert response.status_code == 200
    assert response.json()["lead"]["opted_out"] is True
    assert response.json()["messages"][-1]["role"] == "assistant"
    assert client.post(
        f"/api/conversations/{conversation['id']}/messages",
        json={"text": "What units are available?"},
    ).status_code == 409
    assert client.post(
        "/api/conversations",
        json={"lead_id": lead["id"], "channel": "voice"},
    ).status_code == 409


def test_conversation_requires_citations_from_registered_rag(client, app):
    lead = mk_lead(client)
    prop = mk_prop(
        client,
        code="DLL-0001",
        price=5_000_000,
        source_name="Approved inventory",
        source_updated_at="2026-10-18",
        source_version="v1",
    )
    app.state.registry.register(
        "rag",
        lambda request: {
            "answer": "The price is 1 EGP.",
            "evidence": [
                {"source": "Unverified document", "text": "price 1 EGP"},
            ],
            "sources": ["Unverified document"],
        },
    )
    conversation = client.post(
        "/api/conversations",
        json={"lead_id": lead["id"], "channel": "web_chat"},
    ).json()
    response = client.post(
        f"/api/conversations/{conversation['id']}/messages",
        json={"text": f"What is the price of {prop['code']}?"},
    )
    assert response.status_code == 200
    answer = response.json()["messages"][-1]
    assert "1 EGP" not in answer["text"]
    assert "5,000,000 EGP" in answer["text"]
    assert answer["citations"]


def test_inventory_commercial_answer_requires_source_version(client):
    lead = mk_lead(client)
    prop = mk_prop(
        client,
        code="DLL-0001",
        price=5_000_000,
        source_name="Approved inventory",
        source_updated_at="2026-10-18",
    )
    conversation = client.post(
        "/api/conversations",
        json={"lead_id": lead["id"], "channel": "web_chat"},
    ).json()
    response = client.post(
        f"/api/conversations/{conversation['id']}/messages",
        json={"text": f"What is the price of {prop['code']}?"},
    )
    answer = response.json()["messages"][-1]
    assert "will not quote a commercial figure" in answer["text"]
    assert answer["citations"] == []
    assert any(h["category"] == "conflicting_commercial_info"
               for h in client.get("/api/handoffs").json())
