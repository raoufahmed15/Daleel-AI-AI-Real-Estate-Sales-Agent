# Daleel AI — وحدة الراغ (RAG) بعد إعادة الهيكلة

مساعد مبيعات عقارية يجيب **من مصادر معتمدة فقط**، ويحوّل لمندوب بشري بقرار حتمي في الحالات الحساسة.
كل البيانات اصطناعية (Sandbox). السعر والتوافر يأتيان من جدول الوحدات، والنصوص (FAQ، خطط السداد، الرسوم...) من Qdrant.

## الهيكل

```
app.py                 واجهة Streamlit
src/
  config.py            كل الإعدادات (pydantic-settings + .env)
  models.py            AgentResult / Status / HandoffReason  (العقد مع الـ CRM والـ Dashboard)
  loaders.py           استخراج النص والجداول من PDF عربي بترتيب صحيح (bidi)
  ingest_data.py       يبني Qdrant (النصوص) + جدول الوحدات
  inventory.py         جدول الوحدات + قاعدة أولوية المصادر + سجل التفاعلات (SQLAlchemy: SQLite الآن / MySQL لاحقاً)
  retriever.py         بحث Qdrant مع فلتر (خارجي + صالح بالتاريخ) داخل الاستعلام نفسه
  router.py            تصنيف النية بقواعد حتمية قبل أي LLM
  prompts.py           prompt للتأريض فقط
  guardrails.py        تأريض الأرقام + كشف التسريب
  agent.py             المنسّق
  evaluation.py        تقييم محلي + LangSmith
tests/                 86 اختبار + eval_set.jsonl (105 سؤال)
```

## التشغيل المحلي

```bash
# 1) النموذج
ollama pull qwen3:4b            # ~4.7GB. لجهاز ضعيف: qwen2.5:3b ثم LLM_MODEL=qwen2.5:3b

# 2) البيئة (من جذر المشروع)
python -m venv .venv && source .venv/bin/activate      # ويندوز: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# 3) بناء قواعد المعرفة (أول مرة ينزّل bge-m3 ~2.2GB)
python -m src.ingest_data         # يطبع تحذيرات التحقق إن وُجدت (فارغة = مطابق لملخص كشف التوافر)

# 4) التشغيل
streamlit run app.py
python -m src.agent "ما هي خطط السداد؟"     # من الطرفية

# 5) الاختبار والتقييم
pytest -q                                          # حتمي، بدون Ollama ولا نماذج
python -m src.evaluation --categories unit,handoff # حتمي، بدون LLM
python -m src.evaluation                           # كل الأسئلة (يحتاج Ollama + bge-m3) -> reports/
```

## كيف يعمل السؤال

```
router ──► تحويل فوري (opt_out, delete_data, legal, complaint, confidential, discount, human)   [بلا LLM]
   │
   ├─► رمز وحدة (A-019) ──► inventory ──► جواب حتمي بمصدره (أو تحويل conflict/no_source)       [بلا LLM]
   │                          └─ لو السؤال عن خطة سداد: تُضاف بيانات الوحدة للسياق ويكمل ↓
   └─► Qdrant (مفلتر) ──► LLM ──► NO_ANSWER؟ تسريب؟ رقم غير مؤرَّض؟ ──► تحويل | جواب + مصادر
أي عطل (Ollama / Qdrant / DB) ──► تحويل system_error
```

**قاعدة السعر:** من المستندات الصالحة بتاريخ اليوم، الأحدث بتاريخ الإصدار يغلب (الملحق EXT-09 يغلب v2، وv1 المنتهية تُهمل).
بنفس التاريخ وقيمتين مختلفتين = تعارض = تحويل. **التوافر:** من كشف الوحدات المتاحة فقط.
**المستندات الداخلية (INT-*)** لا تدخل Qdrant ولا الـ prompt إطلاقاً.

## الانتقال إلى MySQL (عندما تجهز البيانات)

1. أنشئ قاعدة بترميز `utf8mb4` وحساباً مخصصاً (`SELECT` على جداول الوحدات، و`INSERT` على `interaction_log`).
2. `pip install pymysql` ثم في `.env`:
   `DATABASE_URL=mysql+pymysql://user:pass@host:3306/daleel?charset=utf8mb4`
3. `python -m src.ingest_data --only inventory` — الجداول تُنشأ تلقائياً (للإنتاج استخدم Alembic).
4. لم يُختبر على MySQL فعلياً: الكود مكتوب بـ SQLAlchemy Core بأطوال أعمدة صريحة ليكون متوافقاً، فجرّبه على نسخة تطوير أولاً.
   إن كانت بيانات الوحدات جاهزة أصلاً هناك، استبدل استخراج الجداول في `ingest_inventory` بقراءة مباشرة منها.

## LangSmith (اختياري)

```
# .env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=daleel-rag-dev
```
- التتبع: كل خطوة (`agent.ask`, `retrieve`) تظهر، والـ `run_id` محفوظ في `AgentResult` وفي `interaction_log`.
- التقييم: `python -m src.evaluation --langsmith --prefix v1` ينشئ Dataset ويشغّل تجربة بنفس المقيّمات المحلية
  (status, reason, docs, facts, forbidden, containment). قارن التجارب جنباً إلى جنب بعد كل تعديل.
- التتبع يرسل المدخلات والمخرجات لخدمة خارجية: مقبول لأن البيانات اصطناعية، ووثّق المزود والمنطقة. لبيانات حقيقية استخدم self-hosted أو أخفِ المدخلات.
- التقييم المحلي (بدون شبكة) هو البديل لـ Demo Day.

## عقد المخرجات

`agent.ask(query, session_id) -> AgentResult(status, reply, intent, reason, sources, latency_ms, timings, run_id)`
عند `opt_out` أو `delete_data`: الراغ يرجع السبب فقط، **وطبقة الـ CRM مسؤولة عن تخزين الإيقاف/الحذف فعلياً** ومنع أي متابعة لاحقة.

## قيود معروفة (اقرأها قبل الاعتماد على الأرقام)

- **لم يُختبر هنا:** bge-m3 وOllama والـ LLM الحقيقي (لا شبكة ولا نماذج في بيئة التطوير). الاختبارات تستخدم تضميناً مزيفاً ولـ LLM مزيف لفحص المنطق فقط.
  شغّل `python -m src.evaluation` محلياً: فئات `faq` و`unit_plan` و`no_source` تقيس الجودة الفعلية، ومتوقع أن تحتاج ضبط `SCORE_THRESHOLD` (الافتراضي 0.5) و`TOP_K`.
- **جودة نصوص الـ PDF:** بعض الكلمات في FAQ تخرج بحرف "ل" في مكان خاطئ (مثل "التسيم") بسبب طريقة توليد الـ PDF نفسه، ولا يمكن إصلاحه من الاستخراج.
  الحل الصحيح: ضع نسخة نصية بجانب الـ PDF بنفس الاسم (`03_faq.md`) وسيُفضَّل تلقائياً (فاصل الصفحات `\f`)، أو أعد توليد الـ PDF بخط/تشكيل عربي سليم.
- **الأرقام في الجواب:** فحص التأريض صارم (أي رقم غير موجود بالسياق = تحويل). لو رأيت تحويلات كثيرة `ungrounded` لأسئلة سليمة، راجع الـ prompt أو خفّف الفحص بناءً على نتائج التقييم.
- **زمن الاستجابة:** هدف الوثيقة median ≤ 5 ثوانٍ. على CPU مع 7B غالباً لن يتحقق؛ جرّب `qwen2.5:3b` أو GPU. الجداول والتحويلات الحتمية فورية.
- غير مُنفَّذ بعد: ذاكرة المحادثة (كل سؤال مستقل)، reranker، hybrid search.

## قرارات تحتاج موافقة الفريق

1. جواب سعر وحدة بمصدر صالح (المطبّق) مقابل تحويل دائم.
2. أولوية الملحق على v2: لاحظ أن T-004 في الملحق (11,255,000) أقل من v2 (11,725,000) — تأكد أنه مقصود.
3. خصم الدفع كاش المنشور (EXT-10) يُذكر للعميل؛ أي طلب خصم إضافي أو تفاوض يتحول لمندوب.
