"""تصنيف نية السؤال بقواعد حتمية قبل أي استدعاء للـ LLM.

ليش؟ حالات التحويل الإجباري (INT-16) وإيقاف التواصل (EXT-13) لازم تنجح 100%،
وهذا ما لا يُضمن لو اعتمدنا على موديل 7B يكتب كلمة سرية. القواعد هنا محافظة بالاتجاه الآمن:
عند الشك في طلب حساس => تحويل لمندوب.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from src.models import HandoffReason


class Intent(str, Enum):
    OPT_OUT = "opt_out"
    DELETE_DATA = "delete_data"
    LEGAL = "legal"
    COMPLAINT = "complaint"
    CONFIDENTIAL = "confidential"
    DISCOUNT_REQUEST = "discount_request"
    HUMAN_REQUEST = "human_request"
    UNIT_LOOKUP = "unit_lookup"
    GENERAL = "general"


INTENT_TO_REASON = {
    Intent.OPT_OUT: HandoffReason.OPT_OUT,
    Intent.DELETE_DATA: HandoffReason.DELETE_DATA,
    Intent.LEGAL: HandoffReason.LEGAL,
    Intent.COMPLAINT: HandoffReason.COMPLAINT,
    Intent.CONFIDENTIAL: HandoffReason.CONFIDENTIAL,
    Intent.DISCOUNT_REQUEST: HandoffReason.DISCOUNT,
    Intent.HUMAN_REQUEST: HandoffReason.HUMAN_REQUEST,
}


@dataclass(frozen=True)
class Route:
    intent: Intent
    unit_codes: tuple[str, ...] = ()
    wants_plan: bool = False

    @property
    def handoff_reason(self) -> HandoffReason | None:
        return INTENT_TO_REASON.get(self.intent)


_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_MARKS = re.compile(r"[\u064B-\u065F\u0670\u0640]")


def normalize(text: str) -> str:
    t = _MARKS.sub("", text.translate(_DIGITS).lower())
    t = re.sub("[أإآٱ]", "ا", t)
    return t.replace("ى", "ي").replace("ة", "ه")


def _rx(*patterns: str) -> re.Pattern:
    return re.compile("|".join(f"(?:{normalize(p)})" for p in patterns))


OPT_OUT_WORDS = {"ايقاف", "stop", "unsubscribe", "وقف", "توقف", "كفي"}
OPT_OUT = _rx(
    r"(ايقاف|وقف|اوقف|توقف|الغاء|الغي).{0,20}(الرسايل|الرسائل|التواصل|المتابعه|الاتصال|المراسله|الاشتراك)",
    r"(لا|ما|مو|مش)\s+(تراسل|ترسل|تتواصل|تتصل|تكلم)",
    r"\b(unsubscribe|opt[\s-]?out)\b", r"stop\s+(messag|text|contact|send|call)",
    r"بلاش\s+(رسايل|رسائل|اتصالات|مكالمات)")
DELETE_DATA = _rx(
    r"(احذف|امسح|ازل|الغي|شيل).{0,20}(بياناتي|معلوماتي|رقمي|حسابي|بيانات)",
    r"حذف\s+(بياناتي|معلوماتي|بيانات)", r"(delete|erase|remove)\s+(my\s+)?(data|information|account)",
    r"حقي\s+في\s+(الحذف|المسح)")
LEGAL = _rx(
    r"قانون", r"محامي|محامين", r"قضائي|قضيه|محكمه|تقاضي|التحكيم", r"شهر\s*(ال)?عقاري|توثيق",
    r"تسجيل\s+(العقد|الوحده|الملكيه|الشقه)", r"ملكيه\s*(الوحده|الشقه)", r"نزاع",
    r"\b(legal|lawyer|lawsuit|court|sue)\b")
COMPLAINT = _rx(
    r"شكوي|اشتك", r"(غير|مش|مو|ماني)\s*(راض|راضي|راضيه)", r"مستاء|محبط|زعلان|معصب|غاضب",
    r"(خدمه|تعامل)\s*(سيئ|سيء|وحش|زفت)", r"نصب|احتيال|نصابين|حرامي", r"تعويض",
    r"\b(complain|complaint|unhappy|scam|fraud)\b")
CONFIDENTIAL = _rx(
    r"راتب|مرتب|رواتب", r"هامش\s*(ال)?ربح|ارباح\s*الشركه|تكلفه\s*(الوحده|البناء)",
    r"(سعر|خصم)\s*(ال)?موظف", r"صلاحيات?\s*(ال)?(خصم|مندوب|مدير)",
    r"دليل\s*المبيعات|playbook", r"(سياسه|قواعد|مستند|مستندات|معايير)\s*(ال)?(داخلي|سري)",
    r"\bint-?\d{2}\b", r"(تجاهل|انسي|ignore|forget).{0,25}(التعليمات|تعليماتك|instructions|rules|القواعد)",
    r"\b(internal|confidential)\b", r"بيانات\s*(داخليه|سريه)",
    r"معايير\s*(تصنيف|العميل)|العميل\s*الساخن|lead\s*scor")
MAX_DISCOUNT = _rx(r"(الاقصي|اقصي|الاعلي|اعلي|اكبر)\s*(نسبه\s*)?(ممكنه?\s*)?(ل|لل)?(ال)?خصم", r"(حد|الحد)\s*(ال)?خصم")
NEGOTIATION = _rx(
    r"تفاوض|فاصل|اخر\s*سعر|اقل\s*سعر|سعر\s*خاص|استثناء|استثنائي",
    r"خصم\s*(اضافي|اكتر|اكثر|اكبر|زياده|خاص)", r"(اضافي|اكتر|اكثر|اكبر|زياده)\s*(ال)?خصم",
    r"\b(negotiat\w*|best\s+price|last\s+price|extra\s+discount)\b")
ASK_DISCOUNT = _rx(r"(بدي|ابغي|عايز|عاوز|اريد|ممكن|تعطيني|اعطني|اعطيني|تديني|ينفع).{0,20}(خصم|تخفيض|تنزيل)")
PUBLISHED_PLAN = _rx(r"كاش|نقد|خطه|خطط|سداد|تقسيط")
HUMAN = _rx(
    r"(اكلم|اتكلم|اتحدث|كلم|حول|تواصل|يتواصل|يكلمني|اتصل|يتصل|عايز|عاوز|بدي|اريد|ابغي|ممكن|خليه).{0,25}"
    r"(مندوب|ممثل|موظف|انسان|شخص\s*حقيقي|بشري|مدير\s*المبيعات|حد\s+(يكلمني|يرد))",
    r"\b(human|real\s+person|representative)\b", r"talk\s+to\s+(a\s+|an\s+)?(agent|rep|someone|person)")
UNIT_RX = re.compile(r"(?<![a-z])([a-z])\s*-?\s*(\d{3})(?!\d)")
PLAN_WORDS = _rx(r"قسط|اقساط|مقدم|خطه|خطط|سداد|تقسيط|كاش|دفعه")


FOLLOWUP_UNIT = _rx(
    r"(هذه|هاي|هادي|هذي|نفس|تلك)\s*(ال)?وحده",
    r"الوحده\s*(نفسها|هاي|هذه)",
    r"(سعر|دور|قسط|اقساط|مقدم|مساحت|اطلالت|حديقت)(ها|ه)\b",
    r"بكم\s*(هي|هو)\b",
    r"\b(هي|هو|ما\s*زالت|لسا|لسه)\s*(ال)?(متاح|محجوز|مباع)",
    r"^(و|هل|وهل)?\s*(متاح|محجوز|مباع)",
    r"(خطه|خطط|سداد|تقسيط|قسط|اقساط|كاش).{0,12}\b(لها|له|لهذه)\b",
    r"\b(is\s+it|this\s+unit|that\s+unit|its\s+price)\b")


def is_unit_followup(text: str) -> bool:
    """سؤال متابعة عن وحدة سبق ذكرها ("هل هي متاحة؟"، "وسعرها؟") بلا كود وحدة صريح."""
    return bool(FOLLOWUP_UNIT.search(normalize(text)))


def asks_plan(text: str) -> bool:
    return bool(PLAN_WORDS.search(normalize(text)))



def route(text: str) -> Route:
    t = normalize(text)
    bare = re.sub(r"[^\w\s]", "", t).strip()
    if bare in OPT_OUT_WORDS or OPT_OUT.search(t):
        return Route(Intent.OPT_OUT)
    if DELETE_DATA.search(t):
        return Route(Intent.DELETE_DATA)
    if LEGAL.search(t):
        return Route(Intent.LEGAL)
    if COMPLAINT.search(t):
        return Route(Intent.COMPLAINT)
    published = bool(PUBLISHED_PLAN.search(t))
    if CONFIDENTIAL.search(t) or (MAX_DISCOUNT.search(t) and not published):
        return Route(Intent.CONFIDENTIAL)
    if NEGOTIATION.search(t) or (ASK_DISCOUNT.search(t) and not published):
        return Route(Intent.DISCOUNT_REQUEST)
    if HUMAN.search(t):
        return Route(Intent.HUMAN_REQUEST)
    codes = tuple(dict.fromkeys(f"{m.group(1).upper()}-{m.group(2)}" for m in UNIT_RX.finditer(t)))
    if codes:
        return Route(Intent.UNIT_LOOKUP, codes, wants_plan=bool(PLAN_WORDS.search(t)))
    return Route(Intent.GENERAL)
