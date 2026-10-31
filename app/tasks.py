"""Celery app and the asynchronous ingestion task for GREP AI."""
import logging
import sys
from pathlib import Path

import redis
from celery import Celery

from app.config import settings
from app.ingestion import iter_chunks
from app.schemas import JobState
from app import storage

log = logging.getLogger("grep_ai.tasks")

celery_app = Celery("grep_ai", broker=settings.redis_url)
celery_app.conf.update(
    task_ignore_result=True,  # job state lives in the Redis job store, not here
    task_acks_late=True,  # redeliver if the worker dies mid-task
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": 3600},
)
if sys.platform == "darwin":
    celery_app.conf.worker_pool = "solo"

# Errors worth retrying. Everything else fails the job immediately.
TRANSIENT_ERRORS = (redis.exceptions.RedisError, ConnectionError, TimeoutError)


def dispatch_ingestion(job_id: str, file_path: str, filename: str) -> None:
    """Send the task to the broker. Raises if the broker is unreachable."""
    ingest_log.apply_async(args=[job_id, file_path, filename], task_id=job_id)


def _fail(job_id: str, message: str) -> None:
    try:
        storage.delete_job_chunks(job_id)  # no partially indexed files
    except Exception:
        log.exception("cleanup failed for job %s", job_id)
    try:
        storage.update_job(job_id, status=JobState.FAILED, error=message)
    except Exception:
        log.exception("could not mark job %s failed", job_id)


@celery_app.task(bind=True, name=settings.celery_task_name)
def ingest_log(self, job_id: str, file_path: str, filename: str) -> None:
    path = Path(file_path)
    try:
        current = storage.get_job(job_id)
        if current is not None and current.status == JobState.COMPLETED:
            log.info("job %s already completed; skipping duplicate delivery", job_id)
            return
        if not path.is_file():
            _fail(job_id, "Uploaded file not found on the worker.")
            return

        storage.update_job(job_id, status=JobState.PROCESSING, error="")
        batch: list[dict] = []
        indexed = lines = 0
        for chunk in iter_chunks(path, job_id=job_id, source_file=filename):
            batch.append(chunk)
            lines = max(lines, chunk["metadata"]["end_line"])
            if len(batch) >= settings.embed_batch_size:
                indexed += storage.upsert_chunks(batch)
                batch = []
                storage.update_job(job_id, lines_processed=lines, chunks_indexed=indexed)
        if batch:
            indexed += storage.upsert_chunks(batch)

        if indexed == 0:
            _fail(job_id, "No parseable log content found.")
            return
        storage.update_job(
            job_id, status=JobState.COMPLETED,
            lines_processed=lines, chunks_indexed=indexed, error="",
        )
        log.info("job %s completed: %d chunks", job_id, indexed)

    except TRANSIENT_ERRORS as exc:
        if self.request.retries >= settings.celery_max_retries:
            log.error("job %s: retries exhausted: %s", job_id, type(exc).__name__)
            _fail(job_id, "Temporary infrastructure error; retries exhausted.")
            return
        countdown = settings.celery_retry_backoff_seconds * (2 ** self.request.retries)
        log.warning("job %s: transient error %s; retrying in %ss",
                    job_id, type(exc).__name__, countdown)
        raise self.retry(exc=exc, countdown=countdown)
    except Exception as exc:  # permanent failure; keep the user-facing message safe
        log.exception("job %s failed", job_id)
        _fail(job_id, f"Ingestion failed ({type(exc).__name__}).")