from langchain_core.documents import Document

from src.guardrails import leaks_internal, numbers_in, only_external, ungrounded_numbers

CTX = "الخصم 15% للمرحلة الثالثة. السعر 9,125,000 جنيه. الوحدة A-019. مدة 3 سنوات. 2026-10-01"


def test_grounded_answer_passes():
    ans = "1. الخصم 15% [EXT-10 v2.0]\n2. السعر 9,125,000 جنيه للوحدة A-019 [EXT-08 v2]"
    assert ungrounded_numbers(ans, CTX, "كم سعر A-019") == []


def test_ungrounded_number_detected():
    assert ungrounded_numbers("الخصم 20%", CTX) == ["20"]
    assert ungrounded_numbers("السعر 9,500,000 جنيه", CTX) == ["9500000"]


def test_arabic_digits_and_separators():
    assert numbers_in("السعر ٩٬١٢٥٬٠٠٠ جنيه") == {"9125000"}
    assert ungrounded_numbers("المدة ٣ سنوات", CTX) == []


def test_numbers_from_query_allowed():
    assert ungrounded_numbers("نعم، ميزانيتك 7,000,000 جنيه", CTX, "ميزانيتي 7,000,000") == []


def test_leak_detection():
    assert leaks_internal("هذا مستند INT-15 غير مسموح بمشاركته")
    assert not leaks_internal("الإطلالة داخلية والتشطيب الداخلي كامل")


def test_only_external():
    hits = [(Document(page_content="a", metadata={"scope": "external"}), 1.0),
            (Document(page_content="b", metadata={"scope": "internal"}), 1.0)]
    assert [d.page_content for d, _ in only_external(hits)] == ["a"]
