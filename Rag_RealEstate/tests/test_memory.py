import pytest

from src.agent import RealEstateAgent
from src.models import Status
from src.router import is_unit_followup

from tests.conftest import TODAY, FakeLLM


def make(engine, store=None, llm=None, **kw):
    return RealEstateAgent(llm=llm or FakeLLM(), store=store, engine=engine, today=TODAY,
                           log_interactions=False, **kw)


@pytest.mark.parametrize("text", ["هل هي متاحة؟", "وسعرها؟", "كم سعرها", "بكم هي؟", "ما مساحتها؟",
                                  "هذه الوحدة متاحة؟", "وخطة السداد لها؟", "متاحة؟", "is it available?"])
def test_followup_detected(text):
    assert is_unit_followup(text)


@pytest.mark.parametrize("text", ["كم أقل مقدم متاح؟", "ما مواصفات التشطيب الداخلي؟", "هل في خصم على الكاش؟",
                                  "أين يقع المشروع؟", "كم سعر مكان الجراج؟", "ما هي وديعة الصيانة؟"])
def test_general_questions_not_followup(text):
    assert not is_unit_followup(text)


def test_followup_uses_last_unit_without_llm(engine):
    llm, a = FakeLLM(), None
    a = make(engine, llm=llm)
    assert a.ask("كم سعر الوحدة B-405؟", "s1").status is Status.ANSWERED
    r = a.ask("هل هي متاحة؟", "s1")
    assert r.status is Status.ANSWERED and "B-405" in r.reply and "متاحة" in r.reply
    r = a.ask("وسعرها؟", "s1")
    assert "5,950,000" in r.reply and {s.doc_id for s in r.sources} == {"EXT-09", "EXT-11"}
    assert llm.calls == []


def test_sessions_are_isolated(engine, full_store, open_threshold):
    a = make(engine, full_store[0], FakeLLM("NO_ANSWER"))
    a.ask("كم سعر الوحدة B-405؟", "s1")
    r = a.ask("وسعرها؟", "s2")
    assert r.status is Status.HANDOFF and "B-405" not in r.reply


def test_no_session_no_memory(engine, full_store, open_threshold):
    a = make(engine, full_store[0], FakeLLM("NO_ANSWER"))
    a.ask("كم سعر الوحدة B-405؟")
    assert a.ask("وسعرها؟").status is Status.HANDOFF


def test_new_explicit_unit_replaces_memory(engine):
    a = make(engine)
    a.ask("سعر A-019", "s1")
    a.ask("سعر B-405", "s1")
    assert "5,950,000" in a.ask("وسعرها؟", "s1").reply


def test_unknown_unit_is_not_remembered(engine, full_store, open_threshold):
    a = make(engine, full_store[0], FakeLLM("NO_ANSWER"))
    a.ask("كم سعر الوحدة Z-999؟", "s1")
    assert a.ask("وسعرها؟", "s1").status is Status.HANDOFF


def test_opt_out_clears_memory(engine, full_store, open_threshold):
    a = make(engine, full_store[0], FakeLLM("NO_ANSWER"))
    a.ask("كم سعر الوحدة B-405؟", "s1")
    a.ask("إيقاف", "s1")
    assert a.ask("وسعرها؟", "s1").status is Status.HANDOFF


def test_followup_with_plan_question_sends_unit_facts_to_llm(engine, full_store, open_threshold):
    llm = FakeLLM("سعر الوحدة 5,950,000 جنيه [EXT-09 v2-ملحق]")
    a = make(engine, full_store[0], llm)
    a.ask("كم سعر الوحدة B-405؟", "s1")
    r = a.ask("وخطة السداد لها؟", "s1")
    assert r.status is Status.ANSWERED and len(llm.calls) == 1
    assert "B-405" in llm.calls[0] and "5,950,000" in llm.calls[0]


def test_general_question_after_unit_is_not_hijacked(engine, full_store, open_threshold):
    llm = FakeLLM("NO_ANSWER")
    a = make(engine, full_store[0], llm)
    a.ask("كم سعر الوحدة B-405؟", "s1")
    a.ask("كم أقل مقدم متاح؟", "s1")
    assert len(llm.calls) == 1 and "B-405" not in llm.calls[0].split("Context:")[1].split("Customer question:")[0]


def test_memory_is_capped(engine):
    a = make(engine, memory_max=2)
    for i, code in enumerate(["A-019", "A-001", "B-405"]):
        a.ask(f"سعر {code}", f"s{i}")
    assert list(a._memory) == ["s1", "s2"]
