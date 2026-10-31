
from pathlib import Path
from textwrap import dedent

ROOT = Path.cwd()

FILES = {
    "app/__init__.py": '''"""AI log observability application."""\n''',

    "app/config.py": '''
"""Central configuration without .env files or virtual environments."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(ROOT / "uploads")))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "25"))
TOP_K = int(os.getenv("TOP_K", "5"))

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8001"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "system_logs")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "text-embedding-3-small"
)

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
''',

    "app/schemas.py": '''
"""Validated API request and response models."""
from typing import Any, Literal
from pydantic import BaseModel, Field


class IngestionAccepted(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    error: str | None = None


class QueryFilters(BaseModel):
    severity: list[str] | None = None
    service: str | None = None
    error_code: str | None = None
    start_time: str | None = None
    end_time: str | None = None


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    filters: QueryFilters = Field(default_factory=QueryFilters)


class Evidence(BaseModel):
    chunk_id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RCAResponse(BaseModel):
    answer: str
    likely_root_cause: str
    confidence: Literal["low", "medium", "high"]
    timeline: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    filters_applied: dict[str, Any] = Field(default_factory=dict)
''',

    "app/ingestion.py": '''
"""Deterministic log parsing and event-aware chunking."""
import re
from datetime import datetime

TIMESTAMP_PATTERN = re.compile(
    r"^(?P<timestamp>\\d{4}-\\d{2}-\\d{2}[ T]\\d{2}:\\d{2}:\\d{2})"
)
SEVERITY_PATTERN = re.compile(
    r"\\b(?P<severity>ERROR|WARN|WARNING|INFO|DEBUG|CRITICAL)\\b",
    re.IGNORECASE,
)
ERROR_CODE_PATTERN = re.compile(
    r"\\b(?:error_code|code)=?(?P<code>[A-Z][A-Z0-9_-]+)\\b",
    re.IGNORECASE,
)
SERVICE_PATTERN = re.compile(r"\\[(?P<service>[\\w.-]+)\\]")


def parse_line(line: str) -> dict:
    """Extract available metadata without inventing missing values."""
    timestamp_match = TIMESTAMP_PATTERN.search(line)
    severity_match = SEVERITY_PATTERN.search(line)
    service_match = SERVICE_PATTERN.search(line)
    error_match = ERROR_CODE_PATTERN.search(line)

    timestamp = None
    if timestamp_match:
        timestamp = datetime.strptime(
            timestamp_match.group("timestamp").replace("T", " "),
            "%Y-%m-%d %H:%M:%S",
        ).isoformat()

    severity = severity_match.group("severity").upper() if severity_match else None
    if severity == "WARNING":
        severity = "WARN"

    return {
        "timestamp": timestamp,
        "severity": severity,
        "service": service_match.group("service") if service_match else None,
        "error_code": error_match.group("code") if error_match else None,
        "text": line.rstrip("\\n"),
    }


def parse_file(path: str) -> list[dict]:
    """Parse a UTF-8 log file, preserving unrecognized lines."""
    events = []
    with open(path, encoding="utf-8", errors="replace") as file:
        for line in file:
            if line.strip():
                events.append(parse_line(line))
    return events


def chunk_events(events: list[dict], chunk_size: int = 50) -> list[list[dict]]:
    """Create ordered chunks; keep the implementation deterministic."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    return [
        events[index:index + chunk_size]
        for index in range(0, len(events), chunk_size)
    ]
''',

    "app/storage.py": '''
"""ChromaDB connection and persistent collection access."""
import chromadb
from app.config import CHROMA_HOST, CHROMA_PORT, CHROMA_COLLECTION


def get_collection():
    """Connect to the ChromaDB service and return the log collection."""
    client = chromadb.HttpClient(
        host=CHROMA_HOST,
        port=CHROMA_PORT,
    )
    return client.get_or_create_collection(name=CHROMA_COLLECTION)
''',

    "app/tasks.py": '''
"""Celery worker and asynchronous log ingestion."""
from celery import Celery
from app.config import REDIS_URL

celery_app = Celery(
    "log_observability",
    broker=REDIS_URL,
    backend=REDIS_URL,
)
celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_log_file",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def ingest_log_file(self, job_id: str, file_path: str):
    """TODO: Parse, embed, persist, and record durable job status."""
    raise NotImplementedError(
        "Implement the ingestion and job-status pipeline in the next milestone."
    )
''',

    "app/retrieval.py": '''
"""Metadata-filtered retrieval and evidence-grounded RCA."""
from app.config import TOP_K


def build_metadata_filter(filters: dict) -> dict | None:
    """TODO: Validate filters and construct a ChromaDB-compatible where clause."""
    raise NotImplementedError


def retrieve_evidence(question: str, filters: dict) -> list[dict]:
    """TODO: Apply database-side metadata filters before vector ranking."""
    raise NotImplementedError


def answer_question(question: str, filters: dict) -> dict:
    """TODO: Generate structured RCA from retrieved evidence only."""
    raise NotImplementedError
''',

    "app/main.py": '''
"""FastAPI endpoints for ingestion, job status, and RCA."""
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from app.config import MAX_UPLOAD_MB, UPLOAD_DIR
from app.schemas import QueryRequest

app = FastAPI(
    title="AI Log Observability API",
    version="0.1.0",
    description="Asynchronous log ingestion and evidence-grounded RCA.",
)

# TODO: Add a durable job-status store and handle broker dispatch failures.


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/ingestion", status_code=status.HTTP_202_ACCEPTED)
async def upload_log(file: UploadFile = File(...)):
    """Validate and persist a log file, then enqueue asynchronous ingestion."""
    if not file.filename or not file.filename.lower().endswith(".log"):
        raise HTTPException(400, "Upload a .log file.")

    job_id = __import__("uuid").uuid4().hex
    destination = UPLOAD_DIR / f"{job_id}.log"
    size = 0

    try:
        with destination.open("wb") as output:
            while True:
                block = await file.read(1024 * 1024)
                if not block:
                    break
                size += len(block)
                if size > MAX_UPLOAD_MB * 1024 * 1024:
                    raise HTTPException(413, "File exceeds the upload limit.")
                output.write(block)

        if size == 0:
            raise HTTPException(400, "The uploaded file is empty.")

        # TODO: Enqueue ingest_log_file.delay(job_id, str(destination)).
        # Return queued only after dispatch succeeds.
        raise HTTPException(
            501,
            "Upload storage works; Celery dispatch is not implemented yet.",
        )
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


@app.get("/api/v1/ingestion/{job_id}")
def get_job_status(job_id: str):
    # TODO: Read the job from the chosen status store.
    raise HTTPException(501, "Job-status storage is not implemented yet.")


@app.post("/api/v1/query")
def query_logs(request: QueryRequest):
    # TODO: Validate time ranges and call the retrieval/RCA pipeline.
    raise HTTPException(501, "Retrieval and RCA are not implemented yet.")
''',

    "tests/test_pipeline.py": '''
"""Initial deterministic tests."""
from app.ingestion import parse_line, chunk_events


def test_parse_error_line():
    event = parse_line(
        "2026-10-27 03:00:05 ERROR [database-service] "
        "Connection timeout error_code=DB_TIMEOUT"
    )
    assert event["severity"] == "ERROR"
    assert event["service"] == "database-service"
    assert event["error_code"] == "DB_TIMEOUT"
    assert event["timestamp"] == "2026-10-27T03:00:05"


def test_chunk_events_preserves_order():
    events = [{"text": str(i)} for i in range(5)]
    chunks = chunk_events(events, chunk_size=2)
    assert [[item["text"] for item in chunk] for chunk in chunks] == [
        ["0", "1"], ["2", "3"], ["4"]
    ]
''',

    "sample_logs/application.log": '''
2026-10-27 02:59:40 INFO [auth-service] Authentication successful request_id=req-101
2026-10-27 02:59:48 INFO [api-service] Incoming GET /orders request_id=req-102
2026-10-27 03:00:01 WARN [database-service] Connection pool utilization reached 90 percent
2026-10-27 03:00:05 ERROR [database-service] Connection timeout error_code=DB_TIMEOUT request_id=req-103
2026-10-27 03:00:06 ERROR [order-service] Database operation failed request_id=req-103
2026-10-27 03:00:08 WARN [order-service] Request retry initiated request_id=req-103
2026-10-27 03:00:18 ERROR [database-service] Connection timeout error_code=DB_TIMEOUT request_id=req-104
2026-10-27 03:00:20 ERROR [api-service] Request failed HTTP 500 request_id=req-104
2026-10-27 03:01:00 INFO [database-service] Connection pool utilization returned to normal
2026-10-27 03:01:10 INFO [api-service] Health check passed
'''.lstrip(),

    "uploads/.gitkeep": "",

    ".gitignore": '''
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
uploads/*
!uploads/.gitkeep
chroma_data/
.DS_Store
'''.lstrip(),

    "requirements.txt": '''
fastapi
uvicorn[standard]
python-multipart
pydantic
celery[redis]
redis
chromadb
langchain
langchain-openai
pytest
httpx
ruff
'''.lstrip(),

    "Dockerfile": '''
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
RUN mkdir -p /app/uploads
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''.lstrip(),

    "docker-compose.yml": '''
services:
  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      REDIS_URL: redis://redis:6379/0
      CHROMA_HOST: chromadb
      CHROMA_PORT: 8000
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      OPENAI_MODEL: ${OPENAI_MODEL:-gpt-4.1-mini}
    volumes:
      - ./uploads:/app/uploads
    depends_on:
      - redis
      - chromadb

  worker:
    build: .
    command: celery -A app.tasks:celery_app worker --loglevel=INFO
    environment:
      REDIS_URL: redis://redis:6379/0
      CHROMA_HOST: chromadb
      CHROMA_PORT: 8000
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      OPENAI_MODEL: ${OPENAI_MODEL:-gpt-4.1-mini}
    volumes:
      - ./uploads:/app/uploads
    depends_on:
      - redis
      - chromadb

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  chromadb:
    image: chromadb/chroma:latest
    environment:
      IS_PERSISTENT: "TRUE"
      PERSIST_DIRECTORY: /chroma/chroma
    volumes:
      - chroma_data:/chroma/chroma
    ports:
      - "8001:8000"

volumes:
  redis_data:
  chroma_data:
'''.lstrip(),

    "README.md": '''
# AI Log Observability and Root Cause Analysis

## Stack
- FastAPI for REST endpoints
- Celery and Redis for asynchronous ingestion
- ChromaDB for vector storage and metadata filtering
- LangChain and OpenAI for retrieval-augmented generation
- Docker Compose for service deployment

## Run directly from the repository root

Install dependencies into the Python installation selected by `python3`:

    python3 -m pip install -r requirements.txt

Set the LLM key in the shell when using OpenAI:

    export OPENAI_API_KEY="your-key"

Start Redis and ChromaDB:

    docker compose up -d redis chromadb

Start the API:

    python3 -m uvicorn app.main:app --reload

Start the worker in another terminal:

    python3 -m celery -A app.tasks:celery_app worker --loglevel=INFO

API documentation: http://localhost:8000/docs

## Important status

This repository contains a partial implementation. Upload validation, basic log parsing,
and initial tests exist. Celery dispatch, durable job tracking, embedding/indexing,
metadata-filtered retrieval, and RCA still require implementation.

The Docker Compose services use containers, but no local Python virtual environment
is required. API keys are supplied through shell environment variables, not files.
'''.lstrip(),
}


def main():
    created = []
    skipped = []

    for name, content in FILES.items():
        path = ROOT / name
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.exists():
            skipped.append(name)
            continue

        path.write_text(dedent(content), encoding="utf-8")
        created.append(name)

    print(f"\nRepository root: {ROOT}")
    print(f"Created: {len(created)} files")
    print(f"Preserved existing files: {len(skipped)} files")

    for name in created:
        print(f"CREATED  {name}")

    for name in skipped:
        print(f"SKIPPED  {name}")

    print("\nNo virtual environment or .env files were created.")
    print("This is a partial implementation; see README.md.")


if __name__ == "__main__":
    main()
