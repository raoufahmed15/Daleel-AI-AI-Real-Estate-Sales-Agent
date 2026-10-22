from datetime import date

from src.retriever import retrieve

from tests.conftest import TODAY


def _ids(store, q, today=TODAY):
    return {d.metadata["source_id"] for d, _ in retrieve(q, store=store, today=today, k=200, threshold=-1.0)}


def test_index_really_contains_internal_and_expired(full_store):
    _, client, docs = full_store
    scopes = {d.metadata["scope"] for d in docs}
    assert scopes == {"external", "internal"}
    assert client.count("real_estate_docs").count == len(docs)


def test_filter_blocks_internal_docs(full_store):
    store, _, _ = full_store
    for q in ("ما الحد الأقصى للخصم؟", "سياسة التحويل لمندوب", "قواعد المتابعة"):
        assert not {i for i in _ids(store, q) if i.startswith("INT-")}


def test_filter_blocks_expired_and_future_documents(full_store):
    store, _, _ = full_store
    now = _ids(store, "قائمة الأسعار")
    assert "EXT-07" not in now and "EXT-08" in now and "EXT-09" in now  # v1 منتهية
    past = _ids(store, "قائمة الأسعار", date(2026, 5, 1))
    assert "EXT-07" in past and "EXT-08" not in past and "EXT-09" not in past  # v2 والملحق لم يصدرا بعد
    late = _ids(store, "خطط السداد", date(2027, 1, 5))
    assert "EXT-10" not in late and "EXT-08" not in late  # صلاحيتهما انتهت 2026-12-31


def test_ingest_is_idempotent(full_store):
    from src import ingest_data as ing
    from tests.conftest import FakeEmbeddings
    _, client, docs = full_store
    before = client.count("real_estate_docs").count
    ing.ingest_vectors(embeddings=FakeEmbeddings(), client=client, docs=docs, reset=False)
    assert client.count("real_estate_docs").count == before
