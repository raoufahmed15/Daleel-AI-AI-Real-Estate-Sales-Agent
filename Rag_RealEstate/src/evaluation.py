"""تقييم الراغ على tests/eval_set.jsonl (محلي افتراضياً، وLangSmith اختياري).

  python -m src.evaluation                         # كل الأسئلة، تقرير JSON في reports/
  python -m src.evaluation --categories unit,handoff   # الفئات الحتمية فقط (لا تحتاج LLM)
  python -m src.evaluation --langsmith             # نفس الأسئلة كتجربة (experiment) في LangSmith

الأرقام نتائج على بيانات اصطناعية، وليست نتائج إنتاج. كل صف في المجموعة فيه:
  question, expected_status, expected_reason, expected_docs, must_contain, must_not_contain
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from src.config import ROOT
from src.router import normalize

EVAL_SET = ROOT / "tests" / "eval_set.jsonl"
CRITICAL_REASONS = {"opt_out", "delete_data", "complaint", "legal", "confidential", "discount"}


def load_rows(path: Path = EVAL_SET, categories: set[str] | None = None) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [r for r in rows if not categories or r["category"] in categories]


def _norm(t: str) -> str:
    return " ".join(normalize(t).split())


def _has(text: str, needle: str) -> bool:
    a, b = _norm(text), _norm(needle)
    return b in a or b.replace(",", "") in a.replace(",", "")


def score_row(ref: dict, out: dict) -> dict:
    """يرجع {اسم_الفحص: True/False/None}. None = الفحص لا ينطبق على هذا الصف."""
    answered = out["status"] == "answered"
    s = {
        "status": out["status"] == ref["expected_status"],
        "reason": (out.get("reason") == ref["expected_reason"]) if ref.get("expected_reason") else None,
        "docs": (any(d in out.get("sources", []) for d in ref["expected_docs"])
                 if ref.get("expected_docs") and ref["expected_status"] == "answered" else None),
        "facts": (all(_has(out["reply"], x) for x in ref["must_contain"])
                  if ref.get("must_contain") and ref["expected_status"] == "answered" else None),
        "forbidden": (not any(_has(out["reply"], x) for x in ref["must_not_contain"])
                      if ref.get("must_not_contain") else None),
    }
    # لو التقييم يتوقع تحويلاً وحصلنا على جواب، فهذا فشل containment حتى لو لم تُحدَّد "reason"
    s["containment"] = (not answered) if ref["expected_status"] == "handoff" else None
    return s


def passed(scores: dict) -> bool:
    return all(v for v in scores.values() if v is not None)


def run_agent(agent, question: str) -> dict:
    res = agent.ask(question)
    return {"reply": res.reply, "status": res.status.value, "reason": res.reason.value if res.reason else None,
            "sources": [s.doc_id for s in res.sources], "latency_ms": res.latency_ms, "intent": res.intent}


def summarize(results: list[dict]) -> dict:
    def rate(rows):
        return round(sum(r["passed"] for r in rows) / len(rows), 3) if rows else None

    by_cat = defaultdict(list)
    for r in results:
        by_cat[r["category"]].append(r)
    answered = [r for r in results if r["expected_status"] == "answered"]
    handoff = [r for r in results if r["expected_status"] == "handoff"]
    critical = [r for r in handoff if r.get("expected_reason") in CRITICAL_REASONS]
    lat = sorted(r["latency_ms"] for r in results)
    return {
        "n": len(results), "pass_rate": rate(results),
        "supported_answer_rate": rate(answered), "handoff_correctness": rate(handoff),
        "critical_handoff_correctness": rate(critical),
        "by_category": {c: {"n": len(v), "pass_rate": rate(v)} for c, v in by_cat.items()},
        "latency_ms": {"p50": int(statistics.median(lat)), "p95": lat[min(len(lat) - 1, int(len(lat) * 0.95))]} if lat else {},
    }


def run_local(agent, rows: list[dict]) -> dict:
    results = []
    for r in rows:
        out = run_agent(agent, r["question"])
        sc = score_row(r, out)
        results.append({**{k: r[k] for k in ("id", "category", "question", "expected_status", "expected_reason")},
                        **out, "scores": sc, "passed": passed(sc)})
    return {"timestamp": datetime.now().isoformat(timespec="seconds"), "summary": summarize(results),
            "failures": [r for r in results if not r["passed"]], "results": results}


# ------------------------------------------------------------------ LangSmith
def _ls_evaluators():
    def make(name):
        def ev(outputs: dict, reference_outputs: dict) -> dict:
            v = score_row(reference_outputs, outputs)[name]
            return {"key": name, "score": None if v is None else int(v)}
        ev.__name__ = name
        return ev

    return [make(n) for n in ("status", "reason", "docs", "facts", "forbidden", "containment")]


def run_langsmith(agent, rows: list[dict], dataset: str, prefix: str):
    from langsmith import Client

    client = Client()
    if not client.has_dataset(dataset_name=dataset):
        ds = client.create_dataset(dataset, description="Daleel RAG evaluation set (synthetic)")
        client.create_examples(
            inputs=[{"question": r["question"]} for r in rows],
            outputs=[{k: r[k] for k in ("expected_status", "expected_reason", "expected_docs",
                                        "must_contain", "must_not_contain")} for r in rows],
            metadata=[{"id": r["id"], "category": r["category"]} for r in rows],
            dataset_id=ds.id)

    def target(inputs: dict) -> dict:
        return run_agent(agent, inputs["question"])

    return client.evaluate(target, data=dataset, evaluators=_ls_evaluators(), experiment_prefix=prefix,
                           max_concurrency=1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--categories", help="مفصولة بفواصل: unit,unit_plan,faq,handoff,no_source")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--langsmith", action="store_true")
    ap.add_argument("--dataset", default="daleel-rag-eval")
    ap.add_argument("--prefix", default="daleel-rag")
    args = ap.parse_args()

    from src.agent import RealEstateAgent

    rows = load_rows(categories=set(args.categories.split(",")) if args.categories else None)[: args.limit]
    agent = RealEstateAgent()
    if args.langsmith:
        print(run_langsmith(agent, rows, args.dataset, args.prefix))
        return
    report = run_local(agent, rows)
    out = ROOT / "reports" / f"eval_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    for f in report["failures"][:15]:
        bad = [k for k, v in f["scores"].items() if v is False]
        print(f"✗ [{f['id']}] {f['question']}  -> {f['status']}/{f['reason']}  فشل: {bad}")
    print(f"\nالتقرير الكامل: {out}")


if __name__ == "__main__":
    main()
