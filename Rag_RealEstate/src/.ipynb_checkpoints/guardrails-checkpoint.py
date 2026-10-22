"""حماية ما بعد التوليد.

الحماية الأقوى معمارية: المستندات الداخلية لا تدخل الـ index ولا الـ prompt أصلاً، فالموديل لا يراها.
هنا طبقات إضافية:
  1) تأريض الأرقام: أي رقم في الجواب لازم يكون موجوداً في السياق (أو في سؤال العميل) وإلا تحويل.
  2) كشف تسريب علامات المستندات الداخلية.
"""
from __future__ import annotations

import re

from langchain_core.documents import Document

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٬", "01234567890123456789,")
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
LEAK = re.compile(r"غير مسموح بمشاركته|سري\s*[-—]\s*داخلي|internal use only|confidential|\bINT-\d{2}\b", re.I)


def canon(n: str) -> str:
    return n.replace(",", "").lstrip("0") or "0"


def numbers_in(text: str) -> set[str]:
    return {canon(m.group(0).rstrip(",")) for m in NUM.finditer(text.translate(_DIGITS))}


def ungrounded_numbers(answer: str, context: str, query: str = "") -> list[str]:
    body = re.sub(r"\[[^\]]*\]", " ", answer)             # الاقتباسات [EXT-10 v2.0]
    body = re.sub(r"(?m)^\s*\d+[.)]\s+", "", body)        # ترقيم القوائم
    allowed = numbers_in(context) | numbers_in(query)
    return sorted(n for n in numbers_in(body) if n not in allowed)


def leaks_internal(answer: str) -> bool:
    return bool(LEAK.search(answer))


def only_external(hits: list[tuple[Document, float]]) -> list[tuple[Document, float]]:
    """طبقة دفاع ثانية: الفلتر الأساسي يتم داخل Qdrant وقت البحث."""
    return [(d, s) for d, s in hits if d.metadata.get("scope") == "external"]
