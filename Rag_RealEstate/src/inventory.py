"""جدول الوحدات (سعر + توافر) مع قاعدة الأولوية بين المصادر.

مبني على SQLAlchemy Core، فنفس الكود يشتغل مع SQLite الآن ومع MySQL لاحقاً (غيّر DATABASE_URL فقط).
الأسعار والتوافر تُخزَّن كتاريخ لكل مصدر (لا نكتب فوق القديم)، والاختيار يتم وقت الاستعلام:

  السعر  : من المستندات الصالحة بتاريخ اليوم، الأحدث بتاريخ الإصدار يغلب (الملحق يغلب v2، و v1 المنتهية تُهمل).
           لو قيمتان مختلفتان بنفس تاريخ الإصدار الأحدث => تعارض => تحويل لمندوب.
  التوافر: من كشف الوحدات المتاحة الأحدث فقط (يلغي أي توافر سابق)، وأي "حالة" داخل قوائم الأسعار تُهمل.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from functools import lru_cache

from sqlalchemy import (BigInteger, Column, Date, DateTime, Integer, MetaData, String, Table, Text,
                        create_engine, delete, insert, select)
from sqlalchemy.engine import Engine

from src.config import get_settings, get_today
from src.models import Source

log = logging.getLogger("daleel.inventory")
metadata = MetaData()

units = Table(
    "units", metadata,
    Column("code", String(16), primary_key=True),
    Column("phase", String(32)), Column("type", String(64)), Column("floor", String(32)),
    Column("area", Integer), Column("garden", Integer), Column("view", String(32)),
)
unit_prices = Table(
    "unit_prices", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("unit_code", String(16), index=True, nullable=False),
    Column("price", BigInteger, nullable=False),  # جنيه مصري، رقم صحيح
    Column("doc_id", String(16), nullable=False), Column("version", String(32)),
    Column("issue_date", Date, nullable=False), Column("valid_until", Date),
)
unit_availability = Table(
    "unit_availability", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("unit_code", String(16), index=True, nullable=False),
    Column("status", String(16), nullable=False),  # متاحة / محجوزة / مباعة
    Column("doc_id", String(16), nullable=False), Column("version", String(32)),
    Column("issue_date", Date, nullable=False), Column("valid_until", Date),
)
interaction_log = Table(
    "interaction_log", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ts", DateTime, nullable=False), Column("session_id", String(64), index=True),
    Column("query", Text), Column("intent", String(32)), Column("status", String(16)),
    Column("reason", String(32)), Column("sources", Text), Column("latency_ms", Integer),
    Column("run_id", String(64)),
)


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    if url.startswith("sqlite:///"):
        from pathlib import Path
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, pool_pre_ping=True, future=True)
    metadata.create_all(engine)
    return engine


@dataclass
class UnitInfo:
    code: str
    phase: str = ""
    type: str = ""
    floor: str = ""
    area: int | None = None
    garden: int | None = None
    view: str = ""
    price: int | None = None
    price_source: Source | None = None
    status: str | None = None
    status_source: Source | None = None
    conflict: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def sources(self) -> list[Source]:
        return [s for s in (self.price_source, self.status_source) if s]


def _valid(row, today: date) -> bool:
    return row.issue_date <= today and (row.valid_until is None or row.valid_until >= today)


def _src(row, titles: dict[str, str]) -> Source:
    return Source(row.doc_id, titles.get(row.doc_id, ""), row.version or "", row.issue_date.isoformat())


def resolve_all(engine: Engine | None = None, today: date | None = None,
                titles: dict[str, str] | None = None) -> dict[str, UnitInfo]:
    """يحل السعر والتوافر لكل الوحدات (حجم المخزون صغير؛ لمخزون كبير حوّلها لـ SQL view)."""
    engine, today, titles = engine or get_engine(), today or get_today(), titles or {}
    with engine.connect() as c:
        base = {r.code: r for r in c.execute(select(units))}
        prices = c.execute(select(unit_prices)).fetchall()
        avail = c.execute(select(unit_availability)).fetchall()

    out = {code: UnitInfo(code, r.phase or "", r.type or "", r.floor or "", r.area, r.garden, r.view or "")
           for code, r in base.items()}

    by_unit: dict[str, list] = {}
    for r in prices:
        if _valid(r, today):
            by_unit.setdefault(r.unit_code, []).append(r)
    for code, rows in by_unit.items():
        info = out.get(code)
        if info is None:
            continue
        newest = max(r.issue_date for r in rows)
        top = [r for r in rows if r.issue_date == newest]
        if len({r.price for r in top}) > 1:
            info.conflict = True
            info.notes.append("تعارض في السعر بين مصادر بنفس تاريخ الإصدار")
        else:
            info.price, info.price_source = top[0].price, _src(top[0], titles)

    by_unit = {}
    for r in avail:
        if _valid(r, today):
            by_unit.setdefault(r.unit_code, []).append(r)
    for code, rows in by_unit.items():
        info = out.get(code)
        if info is None:
            continue
        newest = max(r.issue_date for r in rows)
        top = [r for r in rows if r.issue_date == newest]
        if len({r.status for r in top}) > 1:
            info.conflict = True
            info.notes.append("تعارض في التوافر")
        else:
            info.status, info.status_source = top[0].status, _src(top[0], titles)
    return out


def get_unit(code: str, engine: Engine | None = None, today: date | None = None,
             titles: dict[str, str] | None = None) -> UnitInfo | None:
    return resolve_all(engine, today, titles).get(code.upper())


def search_units(engine: Engine | None = None, phase: str | None = None, type_contains: str | None = None,
                 max_price: int | None = None, min_area: int | None = None, status: str | None = "متاحة",
                 limit: int = 10, today: date | None = None) -> list[UnitInfo]:
    """للـ Recommendation Engine: ترشيح أولي بالقيود الصلبة."""
    res = []
    for u in resolve_all(engine, today).values():
        if u.conflict or u.price is None:
            continue
        if status and u.status != status:
            continue
        if phase and phase not in u.phase:
            continue
        if type_contains and type_contains not in u.type:
            continue
        if max_price and u.price > max_price:
            continue
        if min_area and (u.area or 0) < min_area:
            continue
        res.append(u)
    return sorted(res, key=lambda u: u.price)[:limit]


def format_unit(u: UnitInfo) -> str:
    """نص عربي للوحدة. كل الأرقام منقولة حرفياً من الجدول."""
    specs = " - ".join(x for x in [
        u.type, u.phase, f"الدور {u.floor}" if u.floor else "",
        f"المساحة {u.area} م²" if u.area else "",
        f"حديقة {u.garden} م²" if u.garden else "",
        f"الإطلالة {u.view}" if u.view else ""] if x)
    lines = [f"الوحدة {u.code}: {specs}"]
    if u.price is not None and u.price_source:
        lines.append(f"- السعر: {u.price:,} جنيه [{u.price_source.label()} بتاريخ {u.price_source.issue_date}] "
                     "(قبل أي خصم لخطة السداد، ولا يشمل وديعة الصيانة أو الجراج أو عضوية النادي)")
    if u.status and u.status_source:
        extra = "" if u.status == "متاحة" else " (غير متاحة للبيع حالياً)"
        lines.append(f"- الحالة: {u.status}{extra} [{u.status_source.label()} بتاريخ {u.status_source.issue_date}]")
    return "\n".join(lines)


def log_interaction(result, query: str, session_id: str | None, engine: Engine | None = None) -> None:
    """سجل التدقيق. أي فشل هنا لا يجوز أن يكسر الرد للعميل."""
    try:
        with (engine or get_engine()).begin() as c:
            c.execute(insert(interaction_log).values(
                ts=datetime.now(timezone.utc).replace(tzinfo=None), session_id=session_id, query=query, intent=result.intent,
                status=result.status.value, reason=result.reason.value if result.reason else None,
                sources=json.dumps([s.label() for s in result.sources], ensure_ascii=False),
                latency_ms=result.latency_ms, run_id=result.run_id))
    except Exception as e:  # noqa: BLE001
        log.warning("interaction log failed: %s", e)


def reset_inventory(engine: Engine) -> None:
    with engine.begin() as c:
        for t in (unit_prices, unit_availability, units):
            c.execute(delete(t))
