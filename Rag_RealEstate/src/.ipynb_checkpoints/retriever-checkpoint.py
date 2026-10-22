"""البحث في Qdrant. النماذج والعميل تُحمَّل مرة واحدة فقط (lru_cache)، والفلترة تتم داخل Qdrant وقت البحث."""
from __future__ import annotations

from datetime import date
from functools import lru_cache

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue, Range

from src.config import get_settings, get_today, to_ts
from src.tracing import traceable


@lru_cache
def get_embeddings():
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=get_settings().embedding_model,
        encode_kwargs={"normalize_embeddings": True},
    )


@lru_cache
def get_client() -> QdrantClient:
    s = get_settings()
    return QdrantClient(url=s.qdrant_url) if s.qdrant_url else QdrantClient(path=str(s.qdrant_path))


@lru_cache
def get_store() -> QdrantVectorStore:
    return QdrantVectorStore(client=get_client(), collection_name=get_settings().collection,
                             embedding=get_embeddings())


def build_filter(today: date | None = None) -> Filter:
    """خارجي فقط + صالح بتاريخ اليوم (صدر قبله ولم ينتهِ)."""
    ts = to_ts(today or get_today())
    return Filter(must=[
        FieldCondition(key="metadata.scope", match=MatchValue(value="external")),
        FieldCondition(key="metadata.valid_until_ts", range=Range(gte=ts)),
        FieldCondition(key="metadata.issue_ts", range=Range(lte=ts)),
    ])


@traceable(name="retrieve", run_type="retriever")
def retrieve(query: str, store: QdrantVectorStore | None = None, today: date | None = None,
             k: int | None = None, threshold: float | None = None) -> list[tuple[Document, float]]:
    s = get_settings()
    store = store or get_store()
    return store.similarity_search_with_score(
        query, k=k or s.top_k, filter=build_filter(today),
        score_threshold=s.score_threshold if threshold is None else threshold)
