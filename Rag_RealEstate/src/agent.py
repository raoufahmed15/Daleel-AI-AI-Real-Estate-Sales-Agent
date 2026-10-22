"""منسّق الراغ: router -> (جدول الوحدات | بحث مفلتر + LLM) -> حماية الأرقام -> AgentResult.

كل قرار تحويل يرجع AgentResult فيه status وreason وsources، لتستهلكه طبقة الـ CRM والـ Dashboard.
أي عطل (LLM، قاعدة البيانات، Qdrant) => تحويل system_error، ولا نجيب من ذاكرة الموديل أبداً."""
from __future__ import annotations

import logging
from collections import OrderedDict
from functools import lru_cache
from time import perf_counter

from src import inventory as inv
from src.config import get_settings, get_today
from src.guardrails import leaks_internal, only_external, ungrounded_numbers
from src.loaders import load_manifest
from src.models import AgentResult, HandoffReason, Source, Status
from src.prompts import RAG_PROMPT, build_context
from src.retriever import retrieve
from src.router import Intent, Route, asks_plan, is_unit_followup, route as route_query
from src.tracing import add_metadata, current_run_id, traceable

log = logging.getLogger("daleel.agent")

HANDOFF_MESSAGES = {
    HandoffReason.DISCOUNT: "أي طلب خصم إضافي أو تفاوض على السعر يتم عن طريق مندوب مبيعات. سأحوّلك الآن إلى مندوب ليتواصل معك.",
    HandoffReason.COMPLAINT: "أعتذر عن ذلك، وقد سجّلت ملاحظتك. سأحوّلها إلى مندوب مبيعات ليتواصل معك. لا أستطيع تقديم وعود أو تعويضات بنفسي.",
    HandoffReason.LEGAL: "الأسئلة القانونية المتعلقة بالعقود أو التسجيل أو النزاعات لا أستطيع الإجابة عنها. سأحوّلك إلى مندوب مبيعات لإحالتها إلى الجهة المختصة.",
    HandoffReason.DELETE_DATA: "تم استلام طلب حذف بياناتك، وسيُحوَّل إلى القسم المختص ويُعالج خلال 30 يومًا وفق سياسة الخصوصية.",
    HandoffReason.OPT_OUT: "تم استلام طلبك بإيقاف التواصل، ولن تصلك أي رسائل متابعة.",
    HandoffReason.HUMAN_REQUEST: "بالتأكيد، سأحوّلك الآن إلى مندوب مبيعات ليتواصل معك.",
    HandoffReason.CONFIDENTIAL: "لا أستطيع مشاركة معلومات داخلية خاصة بالشركة. يسعدني مساعدتك بالمعلومات المنشورة عن المشروع، أو تحويلك إلى مندوب مبيعات.",
    HandoffReason.CONFLICT: "لاحظت اختلافًا في بيانات هذه الوحدة بين المصادر، ولذلك سأحوّلك إلى مندوب مبيعات للتأكد من المعلومة الصحيحة.",
    HandoffReason.NO_SOURCE: "لا تتوفر لدي معلومة معتمدة للإجابة عن سؤالك حاليًا. سأحوّلك إلى مندوب مبيعات ليساعدك.",
    HandoffReason.UNGROUNDED: "حرصًا على دقة الأرقام، سأحوّلك إلى مندوب مبيعات لتأكيد هذه المعلومة.",
    HandoffReason.SYSTEM_ERROR: "حدثت مشكلة تقنية مؤقتة. سأحوّلك إلى مندوب مبيعات ليساعدك.",
}


@lru_cache
def get_llm():
    from langchain_ollama import ChatOllama

    s = get_settings()
    return ChatOllama(model=s.llm_model, base_url=s.ollama_base_url, temperature=0, num_ctx=s.llm_num_ctx,
                      keep_alive="30m", client_kwargs={"timeout": s.llm_timeout})


@lru_cache
def _titles() -> dict[str, str]:
    try:
        return {d["doc_id"]: d["title_ar"] for d in load_manifest(get_settings().docs_dir)}
    except Exception:  # noqa: BLE001
        return {}


class RealEstateAgent:
    def __init__(self, llm=None, store=None, engine=None, today=None, log_interactions: bool = True,
                 memory_max: int = 1000):
        self._llm, self.store, self.engine, self.today = llm, store, engine, today
        self.log_interactions = log_interactions
        self._memory: OrderedDict[str, tuple[str, ...]] = OrderedDict()  # آخر وحدات ذكرها كل عميل
        self.memory_max = memory_max

    @property
    def llm(self):
        return self._llm or get_llm()

    # ------------------------------------------------------------- واجهة عامة
    @traceable(name="agent.ask", run_type="chain")
    def ask(self, query: str, session_id: str | None = None) -> AgentResult:
        t0 = perf_counter()
        result = self._ask(query, session_id)
        result.latency_ms = int((perf_counter() - t0) * 1000)
        result.run_id = current_run_id()
        add_metadata(status=result.status.value, intent=result.intent,
                     reason=result.reason.value if result.reason else None,
                     sources=[s.label() for s in result.sources])
        if self.log_interactions:
            inv.log_interaction(result, query, session_id, self.engine)
        return result


    # ------------------------------------------------------------- ذاكرة الوحدة (لكل جلسة)
    def _with_memory(self, r: Route, query: str, session_id: str | None) -> Route:
        if session_id is None:
            return r
        if r.intent in (Intent.OPT_OUT, Intent.DELETE_DATA):
            self._memory.pop(session_id, None)  # إيقاف التواصل أو حذف البيانات: ننسى الجلسة
            return r
        if r.intent is Intent.GENERAL and session_id in self._memory and is_unit_followup(query):
            codes = self._memory[session_id]
            add_metadata(followup_unit=list(codes))
            return Route(Intent.UNIT_LOOKUP, codes, wants_plan=asks_plan(query))
        return r

    def _remember(self, session_id: str | None, codes: tuple[str, ...]) -> None:
        if session_id is None:
            return
        self._memory[session_id] = codes
        self._memory.move_to_end(session_id)
        while len(self._memory) > self.memory_max:  # سقف للذاكرة: نحذف الأقدم
            self._memory.popitem(last=False)
    
    # ------------------------------------------------------------- الداخل
    def _handoff(self, reason: HandoffReason, intent: str, timings: dict | None = None,
                 sources: list[Source] | None = None) -> AgentResult:
        return AgentResult(Status.HANDOFF, HANDOFF_MESSAGES[reason], intent, reason, sources or [],
                           timings=timings or {})

    def _ask(self, query: str, session_id: str | None = None) -> AgentResult:
        timings: dict[str, int] = {}
        today = self.today or get_today()

        r: Route = self._with_memory(route_query(query), query, session_id)
        intent = r.intent.value
        if r.handoff_reason:
            return self._handoff(r.handoff_reason, intent)

        extra, unit_sources = "", []
        if r.intent is Intent.UNIT_LOOKUP:
            t = perf_counter()
            try:
                infos = [inv.get_unit(c, self.engine, today, _titles()) for c in r.unit_codes[:3]]
            except Exception as e:  # noqa: BLE001
                log.error("inventory failure: %s", e)
                return self._handoff(HandoffReason.SYSTEM_ERROR, intent)
            timings["inventory"] = int((perf_counter() - t) * 1000)
            if any(i is not None and i.conflict for i in infos):  # التعارض أولاً: السعر يكون None بسببه
                return self._handoff(HandoffReason.CONFLICT, intent, timings)
            if any(i is None or i.price is None or i.status is None for i in infos):
                return self._handoff(HandoffReason.NO_SOURCE, intent, timings)
            self._remember(session_id, tuple(i.code for i in infos))
            unit_sources = [s for i in infos for s in i.sources]
            facts = "\n\n".join(inv.format_unit(i) for i in infos)
            if not r.wants_plan:
                return AgentResult(Status.ANSWERED, facts + "\n\nهل تحب أن أعرض لك خطط السداد المتاحة؟",
                                   intent, None, _dedupe(unit_sources), timings=timings)
            extra = facts

        t = perf_counter()
        try:
            hits = only_external(retrieve(query, store=self.store, today=today))
        except Exception as e:  # noqa: BLE001
            log.error("retrieval failure: %s", e)
            return self._handoff(HandoffReason.SYSTEM_ERROR, intent, timings)
        timings["retrieve"] = int((perf_counter() - t) * 1000)
        if not hits and not extra:
            return self._handoff(HandoffReason.NO_SOURCE, intent, timings)

        context = build_context(hits, extra)
        prompt = RAG_PROMPT.format(today=today.isoformat(), context=context, query=query)
        t = perf_counter()
        try:
            resp = self.llm.invoke(prompt)
            answer = str(getattr(resp, "content", resp)).strip()
        except Exception as e:  # noqa: BLE001
            log.error("llm failure: %s", e)
            return self._handoff(HandoffReason.SYSTEM_ERROR, intent, timings)
        timings["generate"] = int((perf_counter() - t) * 1000)

        sources = _dedupe(unit_sources + [Source(d.metadata["source_id"], d.metadata.get("title", ""),
                                                 d.metadata.get("version", ""), d.metadata.get("issue_date", ""))
                                          for d, _ in hits])
        if not answer or "NO_ANSWER" in answer:
            return self._handoff(HandoffReason.NO_SOURCE, intent, timings)
        if leaks_internal(answer):
            return self._handoff(HandoffReason.CONFIDENTIAL, intent, timings)
        bad = ungrounded_numbers(answer, context, query)
        if bad:
            log.warning("ungrounded numbers %s in answer", bad)
            add_metadata(ungrounded=bad)
            return self._handoff(HandoffReason.UNGROUNDED, intent, timings)
        return AgentResult(Status.ANSWERED, answer, intent, None, sources, timings=timings)


def _dedupe(sources: list[Source]) -> list[Source]:
    return list(dict.fromkeys(sources))


@lru_cache
def get_agent() -> RealEstateAgent:
    return RealEstateAgent()


def run_real_estate_agent(query: str, session_id: str | None = None) -> str:
    """واجهة قديمة (نص فقط) للتوافق مع الكود السابق."""
    return get_agent().ask(query, session_id).reply


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    q = " ".join(sys.argv[1:]) or "ما هي خطط السداد المتاحة في المشروع؟"
    res = get_agent().ask(q)
    print(res.reply, "\n---", res.status.value, res.reason, [s.label() for s in res.sources], f"{res.latency_ms}ms")
