"""Centralized, non-secret configuration for GREP AI.

Every value can be overridden by an environment variable. Secrets
(NVIDIA_API_KEY) are read on demand and never stored on the settings object.
"""
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _str(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value else default


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    # --- App ---
    app_name: str = "GREP AI"
    tagline: str = "From log search to root cause."
    api_prefix: str = "/api/v1"

    # --- Upload / ingestion ---
    upload_dir: Path = Path(_str("UPLOAD_DIR", str(BASE_DIR / "uploads")))
    max_upload_bytes: int = _int("MAX_UPLOAD_BYTES", 50 * 1024 * 1024)
    allowed_extensions: tuple = (".log",)
    chunk_lines: int = _int("CHUNK_LINES", 50)
    max_chunk_chars: int = _int("MAX_CHUNK_CHARS", 8000)
    embed_batch_size: int = _int("EMBED_BATCH_SIZE", 64)

    # --- Celery / Redis ---
    redis_url: str = _str("REDIS_URL", "redis://localhost:6379/0")
    celery_task_name: str = "grep_ai.ingest_log"
    celery_max_retries: int = _int("CELERY_MAX_RETRIES", 3)
    celery_retry_backoff_seconds: int = _int("CELERY_RETRY_BACKOFF", 5)
    job_ttl_seconds: int = _int("JOB_TTL_SECONDS", 7 * 24 * 3600)

    # --- ChromaDB ---
    # If CHROMA_HOST is set (Docker: "chromadb"), use the HTTP client.
    # Otherwise use a local persistent client at chroma_path.
    chroma_host: str = _str("CHROMA_HOST", "localhost")
    chroma_port: int = _int("CHROMA_PORT", 8001)
    chroma_path: str = _str("CHROMA_PATH", str(BASE_DIR / "chroma_data"))
    chroma_collection: str = _str("CHROMA_COLLECTION", "grep_ai_logs")

    # --- Embeddings (independent of the chat model) ---
    embedding_model: str = _str(
        "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )

    # --- LLM (NVIDIA hosted, OpenAI-compatible) ---
    llm_provider: str = _str("LLM_PROVIDER", "nemotron")
    nvidia_base_url: str = _str("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    nvidia_chat_path: str = "/chat/completions"
    llm_model: str = _str("LLM_MODEL", "nvidia/nemotron-3.5-bolt-e4b")
    llm_timeout_seconds: float = _float("LLM_TIMEOUT_SECONDS", 60.0)
    llm_max_tokens: int = _int("LLM_MAX_TOKENS", 2048)
    llm_temperature: float = _float("LLM_TEMPERATURE", 0.2)
    llm_top_p: float = _float("LLM_TOP_P", 0.95)
    llm_max_retries: int = _int("LLM_MAX_RETRIES", 2)

    # --- Query / retrieval ---
    max_question_chars: int = _int("MAX_QUESTION_CHARS", 1000)
    retrieval_top_k: int = _int("RETRIEVAL_TOP_K", 8)
    retrieval_max_top_k: int = _int("RETRIEVAL_MAX_TOP_K", 25)
    max_context_chars: int = _int("MAX_CONTEXT_CHARS", 12000)

    # --- Metadata vocabulary ---
    severities: tuple = (
        "DEBUG", "INFO", "NOTICE", "WARNING", "ERROR", "CRITICAL",
    )

    @property
    def nvidia_chat_url(self) -> str:
        return self.nvidia_base_url.rstrip("/") + self.nvidia_chat_path


try:  # gitignored file holding the local key; absent in a fresh GitHub clone
    from app.local_secrets import NVIDIA_API_KEY as _HARDCODED_NVIDIA_KEY
except ImportError:
    _HARDCODED_NVIDIA_KEY = ""
def get_nvidia_api_key() -> str | None:
    """Env var wins; otherwise fall back to the hardcoded key."""
    return os.getenv("NVIDIA_API_KEY") or _HARDCODED_NVIDIA_KEY or None

@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()