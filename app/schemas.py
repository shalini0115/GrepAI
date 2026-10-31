"""Pydantic schemas for GREP AI (requests, responses, jobs, evidence, RCA).

Timestamp convention: naive datetimes (no timezone) are interpreted as UTC
consistently at ingestion and at query time. Logs rarely carry a timezone,
so no timezone is invented; both sides simply use the same convention.
"""
from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.config import settings


class JobState(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    app: str
    llm_provider: str
    llm_model: str
    llm_key_configured: bool


# ---------- Ingestion ----------
class IngestionResponse(BaseModel):
    job_id: str
    status: JobState
    filename: str


class JobStatus(BaseModel):
    job_id: str
    status: JobState
    filename: Optional[str] = None
    lines_processed: int = 0
    chunks_indexed: int = 0
    error: Optional[str] = None  # safe, short message only
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------- Query ----------
class QueryFilters(BaseModel):
    """Validated metadata filters. None means 'not specified' (no filtering)."""

    severity: Optional[list[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    service: Optional[str] = Field(default=None, max_length=128)
    error_code: Optional[str] = Field(default=None, max_length=64)
    job_id: Optional[str] = Field(default=None, max_length=64)
    source_file: Optional[str] = Field(default=None, max_length=255)

    @field_validator("severity", mode="before")
    @classmethod
    def _normalize_severity(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            v = [v]
        out = []
        for item in v:
            s = str(item).strip().upper()
            if s == "WARN":
                s = "WARNING"
            if s in ("FATAL", "CRIT"):
                s = "CRITICAL"
            if s not in settings.severities:
                raise ValueError(
                    f"Invalid severity '{item}'. Allowed: {list(settings.severities)}"
                )
            if s not in out:
                out.append(s)
        if not out:
            raise ValueError("severity list must not be empty; omit it instead")
        return out

    @model_validator(mode="after")
    def _check_time_range(self):
        if self.start_time and self.end_time and self.start_time > self.end_time:
            raise ValueError("start_time must be <= end_time")
        return self

    def is_empty(self) -> bool:
        return not any(v is not None for v in self.model_dump().values())


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=settings.max_question_chars)
    filters: QueryFilters = Field(default_factory=QueryFilters)
    top_k: int = Field(
        default=settings.retrieval_top_k, ge=1, le=settings.retrieval_max_top_k
    )

    @field_validator("question")
    @classmethod
    def _strip_question(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("question is too short")
        return v


# ---------- RCA output ----------
class EvidenceItem(BaseModel):
    chunk_id: str
    job_id: str
    source_file: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    timestamp_start: Optional[datetime] = None
    timestamp_end: Optional[datetime] = None
    severity: Optional[str] = None  # highest severity in the chunk
    service: Optional[str] = None
    error_code: Optional[str] = None
    score: Optional[float] = None  # similarity (higher = closer)
    excerpt: str


class TimelineEvent(BaseModel):
    timestamp: Optional[str] = None  # as observed in the logs, never invented
    event: str
    chunk_id: Optional[str] = None


class FiltersApplied(BaseModel):
    """Echo of exactly what was applied inside the vector query."""

    severity: Optional[list[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    service: Optional[str] = None
    error_code: Optional[str] = None
    job_id: Optional[str] = None
    source_file: Optional[str] = None
    chroma_where: Optional[dict] = None  # the actual database-side filter
    candidates_matched: int = 0  # chunks returned by the filtered query


class RCAResponse(BaseModel):
    answer: str
    likely_root_cause: Optional[str] = None
    confidence: Literal["low", "medium", "high", "undetermined"] = "undetermined"
    timeline: list[TimelineEvent] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    filters_applied: FiltersApplied