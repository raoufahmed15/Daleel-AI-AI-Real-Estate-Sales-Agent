from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def app():
    return create_app("sqlite://", auto_seed=False)


@pytest.fixture()
def client(app):
    return TestClient(app)


@pytest.fixture()
def seeded(app):
    from app.seed import seed_database
    with app.state.session_factory() as db:
        seed_database(db)
    return TestClient(app)


def tomorrow_at(hour=10):
    d = datetime.now().date() + timedelta(days=1)
    return datetime(d.year, d.month, d.day, hour).isoformat()


def mk_lead(client, **kw):
    body = {"name": "Test Lead", "phone": "+20 100 111 2222", **kw}
    r = client.post("/api/leads", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def mk_prop(client, **kw):
    body = {"title": "Test Unit", "property_type": "apartment", "location": "New Cairo", "area_sqm": 120,
            "bedrooms": 3, "price": 5_000_000, **kw}
    r = client.post("/api/properties", json=body)
    assert r.status_code == 201, r.text
    return r.json()
