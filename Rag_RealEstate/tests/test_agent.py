import pytest
from sqlalchemy import insert
from datetime import date

from src import inventory as inv
from src.agent import RealEstateAgent
from src.models import HandoffReason as R
from src.models import Status

from tests.conftest import TODAY, FakeLLM, make_engine


def agent(engine, store=None, llm=None):
    return RealEstateAgent(llm=llm or FakeLLM(), store=store, engine=engine, today=TODAY, log_interactions=False)


@pytest.mark.parametrize("q,reason", [
    ("بدي خصم اضافي", R.DISCOUNT), ("عندي شكوى", R.COMPLAINT), ("هل العقد سليم قانونيا؟", R.LEGAL),
    ("احذف بياناتي", R.DELETE_DATA), ("إيقاف", R.OPT_OUT), ("بدي أحكي مع مندوب", R.HUMAN_REQUEST),
    ("ما هو الحد الأقصى للخصم؟", R.CONFIDENTIAL), ("آخر سعر للوحدة A-019؟", R.DISCOUNT),
])
def test_forced_handoffs_never_call_llm_or_search(engine, q, reason):
    llm = FakeLLM()
    res = agent(engine, store=object(), llm=llm).ask(q)  # store=object(): أي بحث سيفشل لو حصل
    assert res.status is Status.HANDOFF and res.reason is reason and llm.calls == []
    assert res.reply and not res.sources


def test_unit_price_answer_is_deterministic_and_sourced(engine):
    llm = FakeLLM()
    res = agent(engine, llm=llm).ask("كم سعر الوحدة B-405؟")
    assert res.status is Status.ANSWERED and llm.calls == []
    assert "5,950,000" in res.reply and "متاحة" in res.reply
    assert {s.doc_id for s in res.sources} == {"EXT-09", "EXT-11"}


def test_unknown_unit_goes_to_human(engine):
    res = agent(engine).ask("كم سعر الوحدة Z-999؟")
    assert res.reason is R.NO_SOURCE


def test_conflicting_unit_goes_to_human(tmp_path):
    from src import ingest_data as ing
    e = make_engine(tmp_path)
    ing.ingest_inventory(engine=e)
    with e.begin() as c:
        c.execute(insert(inv.unit_prices).values(unit_code="A-019", price=1, doc_id="EXT-99", version="x",
                                                 issue_date=date(2026, 7, 1), valid_until=date(2026, 12, 31)))
    assert agent(e).ask("سعر A-019").reason is R.CONFLICT


def test_unit_with_plan_question_uses_llm_with_unit_facts(engine, full_store, open_threshold):
    store = full_store[0]
    llm = FakeLLM("سعر الوحدة A-019 هو 9,125,000 جنيه [EXT-08 v2]")
    res = agent(engine, store, llm).ask("ما هي خطط السداد المتاحة للوحدة A-019؟")
    assert res.status is Status.ANSWERED and len(llm.calls) == 1
    assert "9,125,000" in llm.calls[0] and "[بيانات الوحدة من الجدول المعتمد]" in llm.calls[0]
    assert "EXT-08" in {s.doc_id for s in res.sources}


def _echo(prompt):  # جواب يعيد أسطراً حرفية من السياق => مؤرَّض بالتعريف
    ctx = prompt.split("Context:")[1].split("Customer question:")[0].strip().splitlines()
    return "\n".join(ctx[:3])


def test_general_question_answered_from_filtered_context(engine, full_store, open_threshold):
    store = full_store[0]
    llm = FakeLLM(fn=_echo)
    res = agent(engine, store, llm).ask("ما هي خطط السداد؟")
    assert res.status is Status.ANSWERED
    assert "INT-" not in llm.calls[0]                   # لا مستند داخلي وصل للـ prompt
    assert all(not s.doc_id.startswith("INT-") for s in res.sources)
    assert res.sources and res.timings.get("generate") is not None


@pytest.mark.parametrize("reply,reason", [
    ("NO_ANSWER", R.NO_SOURCE), ("", R.NO_SOURCE),
    ("السعر 123,456,789 جنيه", R.UNGROUNDED),
    ("راجع المستند INT-15", R.CONFIDENTIAL),
])
def test_bad_llm_outputs_become_handoffs(engine, full_store, open_threshold, reply, reason):
    res = agent(engine, full_store[0], FakeLLM(reply)).ask("ما هي خطط السداد؟")
    assert res.status is Status.HANDOFF and res.reason is reason


def test_llm_failure_is_handoff_not_exception(engine, full_store, open_threshold):
    res = agent(engine, full_store[0], FakeLLM(error=TimeoutError("down"))).ask("ما هي خطط السداد؟")
    assert res.reason is R.SYSTEM_ERROR


def test_retrieval_failure_is_handoff(engine):
    class Broken:
        def similarity_search_with_score(self, *a, **k):
            raise RuntimeError("qdrant down")
    res = agent(engine, Broken()).ask("ما هي خطط السداد؟")
    assert res.reason is R.SYSTEM_ERROR


def test_no_relevant_hits_goes_to_human(engine, full_store, monkeypatch):
    from src.config import get_settings
    monkeypatch.setattr(get_settings(), "score_threshold", 0.999)
    llm = FakeLLM()
    res = agent(engine, full_store[0], llm).ask("ما هو سعر الدولار اليوم؟")
    assert res.reason is R.NO_SOURCE and llm.calls == []


def test_interaction_is_logged(tmp_path):
    from sqlalchemy import select
    e = make_engine(tmp_path)
    a = RealEstateAgent(llm=FakeLLM(), engine=e, today=TODAY, log_interactions=True)
    a.ask("إيقاف", session_id="s1")
    with e.connect() as c:
        row = c.execute(select(inv.interaction_log)).fetchone()
    assert row.session_id == "s1" and row.reason == "opt_out" and row.status == "handoff"
