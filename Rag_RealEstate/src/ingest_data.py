"""بناء قواعد المعرفة من documents/ (يشتغل مرة وحدة أو عند تغيّر المستندات).

  python -m src.ingest_data                 # الاثنان
  python -m src.ingest_data --only vectors  # النصوص فقط (Qdrant)
  python -m src.ingest_data --only inventory# الوحدات فقط (SQLite/MySQL)

القرارات:
  * المستندات الداخلية (scope=internal) لا تُفهرس إطلاقاً: هي قواعد تشغيل للنظام وليست معرفة للعميل.
  * مستندات الجداول (EXT-07/08/09/11) تذهب لجدول الوحدات، لا للبحث الدلالي.
  * معرّفات النقاط حتمية (uuid5) فإعادة التشغيل لا تكرر القطع.
"""
from __future__ import annotations

import argparse
import logging
import re
import uuid
from collections import Counter
from datetime import date
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import insert

from src import inventory as inv
from src.config import get_settings, to_ts
from src.loaders import extract_pages, extract_tables, load_manifest, to_int

log = logging.getLogger("daleel.ingest")

PRICE_DOCS = ("EXT-07", "EXT-08", "EXT-09")  # الترتيب مهم: الأحدث آخراً لتحديث مواصفات الوحدة
AVAILABILITY_DOCS = ("EXT-11",)
TABLE_DOCS = set(PRICE_DOCS) | set(AVAILABILITY_DOCS)
UNIT_CODE = re.compile(r"^[A-Z]-\d{3}$")


def _d(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


# ------------------------------------------------------------------ النصوص -> Qdrant
def build_documents(docs_dir: Path | None = None, manifest: list[dict] | None = None, *,
                    include_internal: bool = False, include_tables: bool = False) -> list[Document]:
    """الخياران الاختياريان للاختبارات فقط (للتأكد أن الفلترة تعمل حتى لو دخلت مستندات خاطئة)."""
    s = get_settings()
    docs_dir = Path(docs_dir or s.docs_dir)
    manifest = manifest or load_manifest(docs_dir)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=s.chunk_size, chunk_overlap=s.chunk_overlap, separators=["\n\n", "\n", ".", "،", " "])
    out: list[Document] = []
    for d in manifest:
        if (d["scope"] != "external" and not include_internal) or (d["doc_id"] in TABLE_DOCS and not include_tables):
            continue
        path = docs_dir / d["file"]
        if not path.is_file():
            log.warning("missing file %s", path)
            continue
        header = f"[{d['doc_id']} | {d['title_ar']} | الإصدار {d['version']} | {d['issue_date']}]"
        for page_no, text in enumerate(extract_pages(path), 1):
            for i, chunk in enumerate(splitter.split_text(text)):
                out.append(Document(page_content=f"{header}\n{chunk}", metadata={
                    "source_id": d["doc_id"], "title": d["title_ar"], "version": d["version"],
                    "issue_date": d["issue_date"], "valid_until": d["valid_until"], "scope": d["scope"],
                    "page": page_no, "chunk": i,
                    "issue_ts": to_ts(_d(d["issue_date"])), "valid_until_ts": to_ts(_d(d["valid_until"]))}))
    return out


def _point_id(doc: Document) -> str:
    m = doc.metadata
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{m['source_id']}|{m['version']}|{m['page']}|{m['chunk']}"))


def ingest_vectors(embeddings=None, client=None, reset: bool = True, docs: list[Document] | None = None) -> int:
    from langchain_qdrant import QdrantVectorStore
    from qdrant_client.models import Distance, PayloadSchemaType, VectorParams

    s = get_settings()
    if embeddings is None or client is None:
        from src.retriever import get_client, get_embeddings
        embeddings, client = embeddings or get_embeddings(), client or get_client()
    docs = docs if docs is not None else build_documents()
    dim = len(embeddings.embed_query("test"))
    if reset and client.collection_exists(s.collection):
        client.delete_collection(s.collection)
    if not client.collection_exists(s.collection):
        client.create_collection(s.collection, vectors_config=VectorParams(size=dim, distance=Distance.COSINE))
        for key, schema in (("metadata.scope", PayloadSchemaType.KEYWORD),
                            ("metadata.valid_until_ts", PayloadSchemaType.INTEGER),
                            ("metadata.issue_ts", PayloadSchemaType.INTEGER)):
            if s.qdrant_url:  # الفهارس مفيدة مع سيرفر Qdrant فقط (لا أثر لها بالوضع المحلي)
                client.create_payload_index(s.collection, key, schema)
    store = QdrantVectorStore(client=client, collection_name=s.collection, embedding=embeddings)
    store.add_documents(docs, ids=[_point_id(d) for d in docs])
    log.info("vectors: %d chunks from %d documents", len(docs), len({d.metadata["source_id"] for d in docs}))
    return len(docs)


# ------------------------------------------------------------------ الجداول -> قاعدة الوحدات
def ingest_inventory(engine=None, docs_dir: Path | None = None, manifest: list[dict] | None = None) -> list[str]:
    """يرجع قائمة تحذيرات التحقق (فارغة = كل شيء مطابق لملخص كشف التوافر)."""
    s = get_settings()
    engine = engine or inv.get_engine()
    docs_dir = Path(docs_dir or s.docs_dir)
    by_id = {d["doc_id"]: d for d in (manifest or load_manifest(docs_dir))}
    inv.reset_inventory(engine)

    master: dict[str, dict] = {}
    prices, avail, summary = [], [], {}

    for doc_id in PRICE_DOCS:
        d = by_id.get(doc_id)
        if not d:
            continue
        for table in extract_tables(docs_dir / d["file"]):
            for r in table:
                code = (r.get("unit") or "").upper()
                price = to_int(r.get("price"))
                if not UNIT_CODE.match(code) or price is None:
                    continue
                spec = master.setdefault(code, {})
                spec.update({k: r[k] for k in ("phase", "type", "floor", "view") if r.get(k)})
                for k in ("area", "garden"):
                    if to_int(r.get(k)) is not None:
                        spec[k] = to_int(r[k])
                prices.append(dict(unit_code=code, price=price, doc_id=doc_id, version=d["version"],
                                   issue_date=_d(d["issue_date"]), valid_until=_d(d["valid_until"])))

    for doc_id in AVAILABILITY_DOCS:
        d = by_id.get(doc_id)
        if not d:
            continue
        for table in extract_tables(docs_dir / d["file"]):
            for r in table:
                code = (r.get("unit") or "").upper()
                if UNIT_CODE.match(code) and r.get("status"):
                    spec = master.setdefault(code, {})
                    spec.update({k: r[k] for k in ("phase", "type", "floor", "view") if r.get(k)})
                    if to_int(r.get("area")) is not None:
                        spec["area"] = to_int(r["area"])
                    avail.append(dict(unit_code=code, status=r["status"], doc_id=doc_id, version=d["version"],
                                      issue_date=_d(d["issue_date"]), valid_until=_d(d["valid_until"])))
                elif r.get("phase") and r.get("total"):
                    summary[r["phase"]] = {k: to_int(r.get(k)) for k in ("total", "available", "reserved", "sold")}

    with engine.begin() as c:
        cols = ("phase", "type", "floor", "area", "garden", "view")
        c.execute(insert(inv.units), [dict(code=k, **{x: v.get(x) for x in cols}) for k, v in master.items()])
        if prices:
            c.execute(insert(inv.unit_prices), prices)
        if avail:
            c.execute(insert(inv.unit_availability), avail)
    log.info("inventory: %d units, %d price rows, %d availability rows", len(master), len(prices), len(avail))
    return validate_against_summary(avail, master, summary)


def validate_against_summary(avail: list[dict], master: dict, summary: dict) -> list[str]:
    """مقارنة ما استخرجناه بجدول الملخص الموجود في كشف التوافر نفسه (فحص سلامة للاستخراج)."""
    warnings = []
    if not summary:
        return ["لم يُعثر على جدول ملخص التوافر للمطابقة"]
    counts: dict[str, Counter] = {}
    for a in avail:
        counts.setdefault(master[a["unit_code"]].get("phase", "?"), Counter())[a["status"]] += 1
    names = {"available": "متاحة", "reserved": "محجوزة", "sold": "مباعة"}
    for phase, exp in summary.items():
        got = counts.get(phase, Counter())
        if sum(got.values()) != exp["total"]:
            warnings.append(f"{phase}: العدد الكلي {sum(got.values())} بدل {exp['total']}")
        for key, ar in names.items():
            if got.get(ar, 0) != exp[key]:
                warnings.append(f"{phase}: {ar} {got.get(ar, 0)} بدل {exp[key]}")
    return warnings


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=["vectors", "inventory"])
    ap.add_argument("--no-reset", action="store_true", help="لا تحذف الـ collection قبل الإضافة")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if args.only != "vectors":
        warns = ingest_inventory()
        print("Inventory ready" if not warns else "Validation warnings:\n  " + "\n  ".join(warns))
    if args.only != "inventory":
        count = ingest_vectors(reset=not args.no_reset)
        logging.info("Vector index ready: %d chunks", count)
        from src.retriever import get_client
        get_client().close()        # يسكّر Qdrant صراحة فما يطلع ImportError

if __name__ == "__main__":
    main()
