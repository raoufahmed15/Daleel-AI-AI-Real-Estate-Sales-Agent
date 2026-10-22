from datetime import date

from sqlalchemy import insert

from src import inventory as inv
from src.ingest_data import validate_against_summary
from tests.conftest import TODAY, make_engine


def test_counts(engine):
    units = inv.resolve_all(engine, TODAY)
    assert len(units) == 200
    assert sum(1 for u in units.values() if u.status == "متاحة") == 100  # 18 + 40 + 42 حسب الملخص
    assert sum(1 for u in units.values() if u.status == "محجوزة") == 20  # 6 + 8 + 6
    assert sum(1 for u in units.values() if u.status == "مباعة") == 80   # 36 + 32 + 12


def test_price_precedence_today(engine):
    a = inv.get_unit("A-019", engine, TODAY)          # v2 (v1 منتهية، ولا ملحق لها)
    assert a.price == 9_125_000 and a.price_source.doc_id == "EXT-08" and a.status == "متاحة"
    for code, price in {"B-405": 5_950_000, "F-402": 5_165_000, "C-010": 6_300_000,
                        "E-306": 4_995_000, "T-004": 11_255_000, "C-631": 8_190_000}.items():
        u = inv.get_unit(code, engine, TODAY)
        assert u.price == price and u.price_source.doc_id == "EXT-09", code  # الملحق يغلب v2


def test_expired_and_future_sources(engine):
    u = inv.get_unit("A-019", engine, date(2026, 5, 1))   # قبل v2: v1 فقط، ولا كشف توافر بعد
    assert u.price == 8_485_000 and u.price_source.doc_id == "EXT-07" and u.status is None
    u = inv.get_unit("B-405", engine, date(2026, 7, 15))  # بعد v2 وقبل الملحق
    assert u.price_source.doc_id == "EXT-08" and u.price != 5_950_000
    u = inv.get_unit("A-019", engine, date(2027, 1, 5))   # v2 انتهت صلاحيتها، ولا بديل
    assert u.price is None
    assert inv.get_unit("B-405", engine, date(2027, 1, 5)).price == 5_950_000  # الملحق بلا تاريخ انتهاء


def test_unknown_unit(engine):
    assert inv.get_unit("Z-999", engine, TODAY) is None
    assert inv.get_unit("a-019", engine, TODAY).code == "A-019"


def test_conflict_same_issue_date(tmp_path):
    from src import ingest_data as ing
    e = make_engine(tmp_path)
    ing.ingest_inventory(engine=e)
    with e.begin() as c:
        c.execute(insert(inv.unit_prices).values(unit_code="A-019", price=1, doc_id="EXT-99", version="x",
                                                 issue_date=date(2026, 7, 1), valid_until=date(2026, 12, 31)))
    u = inv.get_unit("A-019", e, TODAY)
    assert u.conflict and u.price is None


def test_search_units(engine):
    res = inv.search_units(engine, phase="الثالثة", type_contains="تاون", today=TODAY, limit=50)
    assert res and all("تاون" in u.type and u.status == "متاحة" for u in res)
    assert [u.price for u in res] == sorted(u.price for u in res)
    cheap = inv.search_units(engine, max_price=5_000_000, today=TODAY, limit=500)
    assert all(u.price <= 5_000_000 for u in cheap)


def test_summary_validation_detects_mismatch():
    avail = [dict(unit_code="A-001", status="متاحة")]
    master = {"A-001": {"phase": "المرحلة الأولى"}}
    summary = {"المرحلة الأولى": dict(total=2, available=1, reserved=1, sold=0)}
    warns = validate_against_summary(avail, master, summary)
    assert any("العدد الكلي" in w for w in warns) and any("محجوزة" in w for w in warns)


def test_format_unit_uses_exact_numbers(engine):
    text = inv.format_unit(inv.get_unit("B-405", engine, TODAY, {"EXT-09": "ملحق قائمة الأسعار"}))
    assert "5,950,000" in text and "EXT-09" in text and "متاحة" in text
