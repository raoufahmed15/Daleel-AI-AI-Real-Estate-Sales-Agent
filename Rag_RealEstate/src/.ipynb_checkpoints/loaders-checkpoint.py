"""استخراج النص والجداول من PDFs العربية بترتيب صحيح.

المشكلة: ملفات PDF هنا تخزّن النص بترتيب بصري، فـ PyMuPDF يعطي الكلمات العربية سليمة
لكن يقلب ترتيب المقاطع داخل السطر (مثلاً "المرحلة الثالثة%10 :" بدل "المرحلة الثالثة: 15%").
هذا يجعل النسب تلتصق بالمرحلة الخطأ، فنصلح الترتيب بخوارزمية bidi قبل التقطيع."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pymupdf
from bidi.algorithm import get_display

_AR = r"\u0600-\u06FF\u0750-\u077F"
HAS_AR = re.compile(f"[{_AR}]")
AR_RUN = re.compile(f"[{_AR}][{_AR}\\s]*[{_AR}]|[{_AR}]")


def fix_text(s: str) -> str:
    """تنظيف عام بعد إعادة الترتيب."""
    s = s.replace("\u0739", "ل")  # حرف تالف في خط الـPDF يظهر مكان "ل" (التسܹيم -> التسليم)
    s = re.sub(r"(?<![\d.,])%(\d+(?:[.,]\d+)?)", r"\1%", s)  # %15 -> 15%
    s = re.sub(rf"(\d)([{_AR}])", r"\1 \2", s)  # 31ديسمبر -> 31 ديسمبر
    s = re.sub(rf"([{_AR}])(\d)", r"\1 \2", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^:\s*(.+)$", r"\1:", s)  # ":خصم الخطة" -> "خصم الخطة:"
    s = re.sub(r"^\.\s*(.+)$", r"\1.", s)  # ".النص" -> "النص." (علامة الترقيم تنتقل في الترتيب البصري)
    s = re.sub(r"^(خصم الخطة) (.+?):$", r"\1: \2", s)  # "خصم الخطة المرحلة الأولى: 5%:" -> "خصم الخطة: المرحلة الأولى: 5%"
    return s


def _span_logical(text: str) -> str:
    if not HAS_AR.search(text):
        return text
    visual = AR_RUN.sub(lambda m: m.group(0)[::-1], text)  # الكلمات العربية إلى ترتيبها البصري
    return get_display(visual, base_dir="R")               # ثم bidi يعيد الترتيب المنطقي


def _render_table(raw: list[list[str]]) -> str:
    """صفوف الجدول كنص "عنوان: قيمة | عنوان: قيمة" حتى لا تلتصق الأرقام بالعمود الخطأ."""
    raw = [r for r in raw if any(r)]
    if not raw:
        return ""
    head = raw[0]
    if len(raw) > 1 and all(head) and not any(re.search(r"\d", h) for h in head):
        return "\n".join(" | ".join(f"{h}: {v}" for h, v in zip(head, row) if v) for row in raw[1:])
    return "\n".join(" | ".join(v for v in row if v) for row in raw)


def page_text(page: pymupdf.Page) -> str:
    tables = page.find_tables().tables
    boxes = [pymupdf.Rect(t.bbox) for t in tables]
    rows = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            x0, y0, x1, y1 = line["bbox"]
            if any(b.contains(pymupdf.Point((x0 + x1) / 2, (y0 + y1) / 2)) for b in boxes):
                continue  # أسطر الجداول تُستخرج بشكل منظم أدناه
            spans = sorted((s for s in line["spans"] if s["text"].strip()), key=lambda s: -s["bbox"][0])
            txt = fix_text(" ".join(_span_logical(s["text"]).strip() for s in spans))
            if txt:
                rows.append((round(y0), txt))
    for t in tables:
        txt = _render_table([[_cell(c) for c in row] for row in t.extract()])
        if txt:
            rows.append((round(t.bbox[1]), txt))
    rows.sort(key=lambda r: r[0])
    return "\n".join(t for _, t in rows)


def extract_pages(pdf_path: Path) -> list[str]:
    """لو يوجد ملف نصي بنفس الاسم بجانب الـPDF (مثلاً 03_faq.md) نفضّله: هو المصدر الأصلي وبلا أخطاء استخراج."""
    for ext in (".md", ".txt"):
        sidecar = Path(pdf_path).with_suffix(ext)
        if sidecar.is_file():
            return [t for t in sidecar.read_text(encoding="utf-8").split("\f")]
    with pymupdf.open(pdf_path) as doc:
        return [page_text(p) for p in doc]


# ---------------------------------------------------------------- الجداول
def _cell(c) -> str:
    c = (c or "").strip()
    if HAS_AR.search(c):  # خلايا الجداول تأتي بترتيب بصري كامل
        c = get_display(c, base_dir="R")
    return fix_text(c)


HEADER_KEYS = {
    "الوحدة": "unit", "المرحلة": "phase", "النوع": "type", "الدور": "floor",
    "المساحة": "area", "الحديقة": "garden", "الإطلالة": "view", "السعر": "price", "الحالة": "status",
    "إجمالي": "total", "متاحة": "available", "محجوزة": "reserved", "مباعة": "sold",
}


def _header_map(row: list[str]) -> dict[int, str] | None:
    mapping = {}
    for i, cell in enumerate(row):
        for key, name in HEADER_KEYS.items():
            if key in cell:
                mapping[i] = name
                break
    return mapping if len(mapping) >= 3 else None


def extract_tables(pdf_path: Path) -> list[list[dict[str, str]]]:
    """كل جدول -> قائمة صفوف (قاموس باسم العمود الإنجليزي). الجدول بلا ترويسة يرث ترويسة السابق."""
    tables, last_header = [], None
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            for t in page.find_tables().tables:
                raw = [[_cell(c) for c in row] for row in t.extract()]
                if not raw:
                    continue
                header = _header_map(raw[0])
                body = raw[1:] if header else raw
                header = header or last_header
                if not header:
                    continue
                last_header = header
                rows = [{name: row[i] for i, name in header.items() if i < len(row)} for row in body if any(row)]
                tables.append(rows)
    return tables


def to_int(s: str | None) -> int | None:
    digits = re.sub(r"[^\d]", "", s or "")
    return int(digits) if digits else None


def load_manifest(docs_dir: Path) -> list[dict]:
    with open(Path(docs_dir) / "manifest.json", encoding="utf-8") as f:
        return json.load(f)["documents"]
