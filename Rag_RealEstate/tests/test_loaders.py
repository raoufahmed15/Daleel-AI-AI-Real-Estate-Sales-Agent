from pathlib import Path

from src.config import ROOT
from src.loaders import extract_pages, fix_text

EXT = ROOT / "documents" / "external"


def test_fix_text_basics():
    assert fix_text("%15") == "15%"
    assert fix_text("31ديسمبر") == "31 ديسمبر"
    assert fix_text("التسܹيم") == "التسليم"
    assert fix_text(":خصم الخطة") == "خصم الخطة:"


def test_discount_percentages_pair_with_correct_phase():
    text = "\n".join(extract_pages(EXT / "10_payment_plans.pdf"))
    for phase, pct in (("الأولى", "5"), ("الثانية", "10"), ("الثالثة", "15")):
        assert f"المرحلة {phase}" in text and f": {pct}%" in text
    import re
    assert re.search(r"المرحلة الأولى\s*:\s*5%،\s*المرحلة الثانية\s*:\s*10%،\s*المرحلة الثالثة\s*:\s*15%", text)


def test_table_rows_keep_column_labels():
    text = "\n".join(extract_pages(EXT / "10_payment_plans.pdf"))
    assert "الخصم: 5% | الخطة: دفع كاش" in text


def test_no_corrupt_glyph_left():
    assert "\u0739" not in "\n".join(extract_pages(EXT / "03_faq.pdf"))
