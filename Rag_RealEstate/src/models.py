"""العقد بين الراغ وباقي المشروع (CRM وDashboard والتقييم)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class Status(str, Enum):
    ANSWERED = "answered"
    HANDOFF = "handoff"


class HandoffReason(str, Enum):
    DISCOUNT = "discount"
    COMPLAINT = "complaint"
    LEGAL = "legal"
    DELETE_DATA = "delete_data"
    OPT_OUT = "opt_out"
    HUMAN_REQUEST = "human_request"
    CONFIDENTIAL = "confidential"
    CONFLICT = "conflict"          # تعارض في السعر أو التوافر
    NO_SOURCE = "no_source"        # لا يوجد مصدر معتمد للإجابة
    UNGROUNDED = "ungrounded"      # رقم في الجواب غير موجود بالمصدر
    SYSTEM_ERROR = "system_error"  # عطل تقني (LLM أو قاعدة البيانات)


@dataclass(frozen=True)
class Source:
    doc_id: str
    title: str = ""
    version: str = ""
    issue_date: str = ""

    def label(self) -> str:
        v = self.version
        return f"{self.doc_id} {v}" if v[:1].lower() == "v" else f"{self.doc_id} v{v}".strip()


@dataclass
class AgentResult:
    status: Status
    reply: str
    intent: str = ""
    reason: HandoffReason | None = None
    sources: list[Source] = field(default_factory=list)
    latency_ms: int = 0
    timings: dict[str, int] = field(default_factory=dict)
    run_id: str | None = None

    @property
    def is_handoff(self) -> bool:
        return self.status is Status.HANDOFF

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        d["reason"] = self.reason.value if self.reason else None
        return d
