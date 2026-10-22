"""LangSmith اختياري: لو الحزمة أو المفتاح غير موجودين، الكود يشتغل بدون أي تتبع.
التفعيل: LANGSMITH_TRACING=true و LANGSMITH_API_KEY و LANGSMITH_PROJECT في .env"""
from __future__ import annotations

from src import config  # noqa: F401  (يحمّل .env قبل langsmith)

try:
    from langsmith import traceable  # noqa: F401
except ImportError:  # pragma: no cover
    def traceable(*args, **kwargs):
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]

        def deco(fn):
            return fn

        return deco


def current_run_id() -> str | None:
    try:
        from langsmith.run_helpers import get_current_run_tree

        rt = get_current_run_tree()
        return str(rt.id) if rt else None
    except Exception:
        return None


def add_metadata(**meta) -> None:
    try:
        from langsmith.run_helpers import get_current_run_tree

        rt = get_current_run_tree()
        if rt:
            rt.add_metadata(meta)
    except Exception:
        pass
