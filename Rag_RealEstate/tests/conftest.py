import hashlib
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pytest
from langchain_core.embeddings import Embeddings
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import ingest_data as ing  # noqa: E402
from src import inventory as inv  # noqa: E402

TODAY = date(2026, 10, 21)


class FakeEmbeddings(Embeddings):
    """تضمين بسيط حتمي (hash لمقاطع الحروف) لاختبار منطق الفلترة بدون تحميل bge-m3."""
    dim = 256

    def _vec(self, text: str):
        v = np.zeros(self.dim)
        t = f"  {text}  "
        for i in range(len(t) - 2):
            v[int(hashlib.md5(t[i:i + 3].encode()).hexdigest(), 16) % self.dim] += 1
        n = np.linalg.norm(v)
        return (v / n if n else v).tolist()

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


class FakeLLM:
    def __init__(self, reply="NO_ANSWER", fn=None, error=None):
        self.reply, self.fn, self.error, self.calls = reply, fn, error, []

    def invoke(self, prompt):
        self.calls.append(prompt)
        if self.error:
            raise self.error
        return self.fn(prompt) if self.fn else self.reply


def make_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'inv.db'}")
    inv.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="session")
def engine(tmp_path_factory):
    e = make_engine(tmp_path_factory.mktemp("db"))
    warnings = ing.ingest_inventory(engine=e)
    assert warnings == [], warnings
    return e


@pytest.fixture(scope="session")
def full_store():
    """index فيه كل المستندات عمداً (داخلية ومنتهية أيضاً) لاختبار أن الفلتر وحده يحمينا."""
    from langchain_qdrant import QdrantVectorStore
    from qdrant_client import QdrantClient

    from src.config import get_settings

    client, emb = QdrantClient(":memory:"), FakeEmbeddings()
    docs = ing.build_documents(include_internal=True, include_tables=True)
    ing.ingest_vectors(embeddings=emb, client=client, docs=docs)
    store = QdrantVectorStore(client=client, collection_name=get_settings().collection, embedding=emb)
    return store, client, docs


@pytest.fixture
def open_threshold(monkeypatch):
    from src.config import get_settings
    monkeypatch.setattr(get_settings(), "score_threshold", -1.0)
