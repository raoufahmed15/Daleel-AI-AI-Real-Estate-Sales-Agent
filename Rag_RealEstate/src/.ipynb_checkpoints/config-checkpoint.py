"""إعدادات المشروع كلها في مكان واحد. القيم تُقرأ من .env أو من متغيرات البيئة."""
from __future__ import annotations

from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")  # يجعل LANGSMITH_* وغيرها متاحة لمكتبات أخرى (pydantic وحده لا يصدّرها لـ os.environ)
NO_EXPIRY_TS = 4102444800  # 2100-01-01: قيمة "بدون تاريخ انتهاء" لتبقى الفلترة بشرط رقمي واحد


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    # المسارات
    docs_dir: Path = ROOT / "documents"
    qdrant_path: Path = ROOT / "qdrant_db"
    qdrant_url: str | None = None  # لو Qdrant شغال كسيرفر (مثلاً http://localhost:6333)
    collection: str = "real_estate_docs"

    # قاعدة بيانات الوحدات: SQLite الآن، وMySQL لاحقاً بتغيير هذا السطر فقط:
    # DATABASE_URL=mysql+pymysql://user:pass@host:3306/daleel?charset=utf8mb4
    database_url: str = f"sqlite:///{ROOT / 'data' / 'inventory.db'}"

    # النماذج
    embedding_model: str = "BAAI/bge-m3"
    llm_model: str = "qwen3:4b"
    ollama_base_url: str = "http://localhost:11434"
    llm_num_ctx: int = 4096
    llm_timeout: int = 120

    # الاسترجاع
    chunk_size: int = 500
    chunk_overlap: int = 80
    top_k: int = 4
    score_threshold: float = 0.5

    # لاختبار سيناريوهات التواريخ (مثلاً TODAY=2026-10-21)
    today: date | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_today() -> date:
    return get_settings().today or date.today()


def to_ts(d: date | None) -> int:
    """تاريخ -> epoch (بداية اليوم UTC). None = بدون انتهاء."""
    if d is None:
        return NO_EXPIRY_TS
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())
