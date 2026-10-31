"""FastAPI application for GREP AI."""
import sys
from pathlib import Path

# Get the repository root directory
ROOT_DIR = Path(__file__).resolve().parent.parent

# Add repository root to Python's module search path
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import logging
import re
import threading
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi import Path as PathParam
from fastapi.responses import HTMLResponse

from app import storage
from app.config import get_nvidia_api_key, settings
from app.graph import build_graph
from app.retrieval import LLMError, answer_query
from app.schemas import HealthResponse, IngestionResponse, JobState, JobStatus, QueryRequest, RCAResponse
from app.tasks import dispatch_ingestion
from app.ui import INDEX_HTML

log = logging.getLogger("grep_ai.api")
P = settings.api_prefix
JOB_RE = r"^[0-9a-f]{32}$"


def _warm() -> None:
    try:
        storage.get_collection()
        storage.get_embedder()
    except Exception:
        log.exception("warm-up failed (will retry lazily)")


@asynccontextmanager
async def lifespan(_: FastAPI):
    threading.Thread(target=_warm, daemon=True).start()
    yield


app = FastAPI(title=settings.app_name, description=settings.tagline, lifespan=lifespan)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index():
    return INDEX_HTML


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        app=settings.app_name, llm_provider=settings.llm_provider,
        llm_model=settings.llm_model, llm_key_configured=get_nvidia_api_key() is not None,
    )


def _discard(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        log.exception("could not remove %s", path)


@app.post(f"{P}/ingestion", response_model=IngestionResponse, status_code=202)
def upload(file: UploadFile = File(...)):
    original = Path(file.filename or "").name
    if Path(original).suffix.lower() not in settings.allowed_extensions:
        raise HTTPException(415, "Only .log files are supported.")
    display = re.sub(r"[^\w.\- ]", "_", original)[:255]

    job_id = uuid.uuid4().hex
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    dest = settings.upload_dir / f"{job_id}.log"
    size, first = 0, True
    try:
        with open(dest, "wb") as out:
            while chunk := file.file.read(1024 * 1024):
                if first and b"\x00" in chunk:
                    raise HTTPException(415, "Binary files are not supported.")
                first = False
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(413, f"File exceeds {settings.max_upload_bytes // (1024 * 1024)} MB.")
                out.write(chunk)
        if size == 0:
            raise HTTPException(400, "The uploaded file is empty.")
    except HTTPException:
        _discard(dest)
        raise
    except OSError:
        _discard(dest)
        log.exception("could not store upload")
        raise HTTPException(500, "Could not store the uploaded file.")

    try:
        storage.create_job(job_id, display)
        dispatch_ingestion(job_id, str(dest), display)
    except Exception:
        log.exception("dispatch failed for job %s", job_id)
        _discard(dest)
        try:
            storage.update_job(job_id, status=JobState.FAILED, error="Could not queue the job.")
        except Exception:
            pass
        raise HTTPException(503, "Could not queue the ingestion job. Is Redis running?")
    return IngestionResponse(job_id=job_id, status=JobState.QUEUED, filename=display)


@app.get(f"{P}/ingestion/{{job_id}}", response_model=JobStatus)
def job_status(job_id: str = PathParam(pattern=JOB_RE)):
    try:
        job = storage.get_job(job_id)
    except Exception:
        log.exception("job store unavailable")
        raise HTTPException(503, "Job store unavailable.")
    if job is None:
        raise HTTPException(404, "Unknown or expired job.")
    return job


@app.post(f"{P}/query", response_model=RCAResponse)
def query(req: QueryRequest):
    try:
        return answer_query(req)
    except LLMError as exc:
        raise HTTPException(exc.status_code, str(exc))
    except Exception:
        log.exception("query failed")
        raise HTTPException(500, "Query failed.")


@app.get(f"{P}/graph")
def graph(job_id: str = Query(pattern=JOB_RE), highlight: str = Query(default="", max_length=4000)):
    ids = [h for h in highlight.split(",") if h][:50]
    try:
        return build_graph(job_id, ids)
    except Exception:
        log.exception("graph failed")
        raise HTTPException(500, "Could not build the graph.")



@app.get("/health/store", include_in_schema=False)
def store_info():
    return {
        "chroma_host": settings.chroma_host or "(local folder)",
        "chroma_port": settings.chroma_port,
        "collection": settings.chroma_collection,
        "chunks_visible": storage.count_chunks(),
    }
