"""الفئات الحتمية من مجموعة التقييم (وحدات + تحويلات) لازم تنجح 100% وبدون أي استدعاء للـ LLM أو البحث."""
from src.agent import RealEstateAgent
from src.evaluation import load_rows, run_local

from tests.conftest import TODAY


class ForbiddenLLM:
    def invoke(self, prompt):
        raise AssertionError("الـ LLM لا يجب أن يُستدعى في الفئات الحتمية")


def test_deterministic_categories_pass_fully(engine):
    agent = RealEstateAgent(llm=ForbiddenLLM(), store=object(), engine=engine, today=TODAY, log_interactions=False)
    report = run_local(agent, load_rows(categories={"unit", "handoff"}))
    assert report["failures"] == [], [(f["id"], f["question"]) for f in report["failures"]]
    assert report["summary"]["critical_handoff_correctness"] == 1.0


def test_eval_set_is_well_formed():
    rows = load_rows()
    assert len(rows) >= 100 and len({r["id"] for r in rows}) == len(rows)
    assert {r["category"] for r in rows} == {"unit", "unit_plan", "faq", "handoff", "no_source"}
