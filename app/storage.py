"""ChromaDB storage, embeddings and the durable job store for GREP AI."""
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

import chromadb
import numpy as np
import redis

from app.config import settings
from app.schemas import JobState, JobStatus

# MiniLM reads ~256 tokens; long chunks are embedded as windows and averaged.
EMBED_WINDOW_CHARS = 700


# ------------------------------------------------------------------ Chroma
@lru_cache
def get_client():
    if settings.chroma_host:
        return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=settings.chroma_path)


@lru_cache
def get_collection():
    return get_client().get_or_create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
        embedding_function=None,  # we always supply embeddings ourselves
    )


# -------------------------------------------------------------- embeddings
@lru_cache
def get_embedder():
    """Loaded once per process (not once per document)."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model)


def _encode(texts: list[str]) -> np.ndarray:
    return get_embedder().encode(
        texts,
        batch_size=settings.embed_batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )


def _windows(doc: str) -> list[str]:
    out: list[str] = []
    cur, size = [], 0
    for line in doc.split("\n"):
        while len(line) > EMBED_WINDOW_CHARS:  # slice very long lines
            if cur:
                out.append("\n".join(cur))
                cur, size = [], 0
            out.append(line[:EMBED_WINDOW_CHARS])
            line = line[EMBED_WINDOW_CHARS:]
        if cur and size + len(line) + 1 > EMBED_WINDOW_CHARS:
            out.append("\n".join(cur))
            cur, size = [], 0
        cur.append(line)
        size += len(line) + 1
    if cur:
        out.append("\n".join(cur))
    return out or [" "]


def embed_documents(docs: list[str]) -> list[list[float]]:
    windows: list[str] = []
    owner: list[int] = []
    for i, d in enumerate(docs):
        for w in _windows(d):
            windows.append(w)
            owner.append(i)
    vecs = _encode(windows)
    out = np.zeros((len(docs), vecs.shape[1]), dtype=np.float32)
    for row, i in zip(vecs, owner):
        out[i] += row
    norms = np.linalg.norm(out, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (out / norms).tolist()


def embed_query(text: str) -> list[float]:
    return _encode([text[:EMBED_WINDOW_CHARS]])[0].tolist()


# ------------------------------------------------------------------ writes
def upsert_chunks(chunks: list[dict]) -> int:
    """Idempotent: same chunk ID overwrites the same record. Returns count written."""
    col = get_collection()
    written = 0
    step = settings.embed_batch_size
    for i in range(0, len(chunks), step):
        batch = chunks[i : i + step]
        docs = [c["document"] for c in batch]
        col.upsert(
            ids=[c["id"] for c in batch],
            documents=docs,
            embeddings=embed_documents(docs),
            metadatas=[c["metadata"] for c in batch],
        )
        written += len(batch)
    return written


def delete_job_chunks(job_id: str) -> None:
    get_collection().delete(where={"job_id": job_id})


# ------------------------------------------------------------------- reads
def count_chunks(where: Optional[dict] = None) -> int:
    col = get_collection()
    if where is None:
        return col.count()
    return len(col.get(where=where, include=[])["ids"])


def query_chunks(question: str, where: Optional[dict], top_k: int) -> list[dict]:
    """Vector query with the metadata filter applied inside Chroma (pre-filter)."""
    res = get_collection().query(
        query_embeddings=[embed_query(question)],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    ids = res["ids"][0]
    return [
        {
            "id": ids[i],
            "document": res["documents"][0][i],
            "metadata": res["metadatas"][0][i],
            "score": 1.0 - float(res["distances"][0][i]),  # cosine similarity
        }
        for i in range(len(ids))
    ]


# --------------------------------------------------------------- job store
@lru_cache
def get_redis():
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def _job_key(job_id: str) -> str:
    return f"grep_ai:job:{job_id}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(job_id: str, filename: str) -> None:
    r, key, now = get_redis(), _job_key(job_id), _now()
    r.hset(key, mapping={
        "status": JobState.QUEUED.value, "filename": filename,
        "lines_processed": 0, "chunks_indexed": 0, "error": "",
        "created_at": now, "updated_at": now,
    })
    r.expire(key, settings.job_ttl_seconds)


def update_job(job_id: str, **fields) -> None:
    mapping = {}
    for k, v in fields.items():
        if isinstance(v, JobState):
            v = v.value
        if k == "error":
            v = (v or "")[:300]
        mapping[k] = "" if v is None else v
    mapping["updated_at"] = _now()
    r, key = get_redis(), _job_key(job_id)
    r.hset(key, mapping=mapping)
    r.expire(key, settings.job_ttl_seconds)


def get_job(job_id: str) -> Optional[JobStatus]:
    data = get_redis().hgetall(_job_key(job_id))
    if not data:
        return None
    return JobStatus(
        job_id=job_id,
        status=data["status"],
        filename=data.get("filename") or None,
        lines_processed=int(data.get("lines_processed") or 0),
        chunks_indexed=int(data.get("chunks_indexed") or 0),
        error=data.get("error") or None,
        created_at=data.get("created_at") or None,
        updated_at=data.get("updated_at") or None,
    )



def get_job_chunks(job_id: str, limit: int = 3000) -> list[dict]:
    """All stored chunks of one upload, ordered by chunk_index (bounded)."""
    col = get_collection()
    out: list[dict] = []
    offset, page = 0, 500
    while offset < limit:
        res = col.get(
            where={"job_id": job_id},
            include=["documents", "metadatas"],
            limit=min(page, limit - offset),
            offset=offset,
        )
        ids = res["ids"]
        if not ids:
            break
        for i, cid in enumerate(ids):
            out.append({"id": cid, "document": res["documents"][i], "metadata": res["metadatas"][i]})
        offset += len(ids)
    out.sort(key=lambda c: c["metadata"].get("chunk_index", 0))
    return out