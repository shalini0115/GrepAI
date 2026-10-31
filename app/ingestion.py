"""Log parsing, metadata extraction and event-aware chunking for GREP AI.

Streams a file, groups lines into events (stack traces stay attached to their
parent), and yields chunks with Chroma-compatible metadata. Nothing is
fabricated: fields that are absent in the log stay absent.
"""
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, Optional

from app.config import settings

SEVERITY_RANK = {
    "DEBUG": 0, "INFO": 1, "NOTICE": 2, "WARNING": 3, "ERROR": 4, "CRITICAL": 5,
}
_SEV_ALIASES = {
    "TRACE": "DEBUG", "DEBUG": "DEBUG", "INFO": "INFO", "NOTICE": "NOTICE",
    "WARN": "WARNING", "WARNING": "WARNING", "ERROR": "ERROR", "ERR": "ERROR",
    "SEVERE": "ERROR", "CRIT": "CRITICAL", "CRITICAL": "CRITICAL",
    "FATAL": "CRITICAL", "ALERT": "CRITICAL", "EMERG": "CRITICAL",
}

MAX_LINE_CHARS = 2000
MAX_FLAGS_PER_CHUNK = 10

# ---------------------------------------------------------------- regexes
_ISO = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})"
    r"(?:[.,](\d{1,6}))?\s*(Z|[+-]\d{2}:?\d{2})?"
)
_APACHE_ERR_TS = re.compile(
    r"^\[(?:\w{3}) (\w{3}) +(\d{1,2}) (\d{2}):(\d{2}):(\d{2})(?:\.\d+)? (\d{4})\]"
)
_APACHE_ACC_TS = re.compile(
    r"\[(\d{2})/(\w{3})/(\d{4}):(\d{2}):(\d{2}):(\d{2}) ([+-]\d{4})\]"
)
_SYSLOG = re.compile(
    r"^[A-Z][a-z]{2} +\d{1,2} \d{2}:\d{2}:\d{2} \S+ ([\w.\-/]+?)(?:\([^)]*\))?(?:\[\d+\])?:"
)
_SEV_BRACKET = re.compile(
    r"\[(emerg|alert|crit|critical|error|err|warn|warning|notice|info|debug)\]", re.I
)
_SEV_BARE = re.compile(
    r"\b(TRACE|DEBUG|INFO|NOTICE|WARN|WARNING|ERROR|SEVERE|CRITICAL|CRIT|FATAL)\b"
)
_SERVICE_KV = re.compile(r"\bservice[=:]\s*\"?([A-Za-z][\w.\-]*)", re.I)
_SERVICE_BRACKET = re.compile(r"^\[([A-Za-z][\w.\-]*)\]")
_SERVICE_DOTTED = re.compile(r"^([A-Za-z][\w\-]*)(?:\.[\w\-]+)+\b")
_SERVICE_COLON = re.compile(r"^([A-Za-z][\w.\-]*):")
_SERVICE_STOP = {
    "error", "exception", "warning", "warn", "failed", "failure", "info",
    "debug", "fatal", "critical", "traceback", "caused", "client", "req",
}
_REQ_ID = re.compile(r"\b(req-[0-9a-fA-F\-]{8,})")
_REQ_ID_KV = re.compile(
    r"(?:request[_-]?id|correlation[_-]?id|trace[_-]?id|x-request-id)[=:\s\"']+([\w\-]{6,})",
    re.I,
)
_ERRNO = re.compile(
    r"\b(ECONNREFUSED|ECONNRESET|ETIMEDOUT|ENOENT|EACCES|EPERM|ENOSPC|EADDRINUSE|"
    r"EPIPE|EIO|ENOMEM|EHOSTUNREACH|ENETUNREACH|EEXIST|EINVAL|EAGAIN|EMFILE)\b"
)
_ERR_UNDERSCORE = re.compile(r"\b(ERR_[A-Z0-9_]+)\b")
_VENDOR_CODE = re.compile(r"\b([A-Z]{2,10}-\d{2,6})\b")
_EXC_NAME = re.compile(r"\b((?:[a-z_]\w*\.)*[A-Z]\w*(?:Exception|Error))\b")
_HTTP_ACCESS = re.compile(r"\"\s([45]\d{2})\s")
_HTTP_KV = re.compile(r"\b(?:status|http)[=: ]+([45]\d{2})\b", re.I)
_CONTINUATION = re.compile(r"^(\s+|Traceback|Caused by:|\.\.\. \d+ more)")

_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}

_SECRET_PATTERNS = [
    (re.compile(r"nvapi-[A-Za-z0-9_\-]{10,}"), "[REDACTED_KEY]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED_KEY]"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{12,}"), "Bearer [REDACTED]"),
    (re.compile(r"(?i)\b(password|passwd|pwd|secret|api[_-]?key|token)\s*[=:]\s*\S+"),
     r"\1=[REDACTED]"),
]


def redact_secrets(text: str) -> str:
    """Mask obvious credentials before text is sent to an external LLM."""
    for pattern, repl in _SECRET_PATTERNS:
        text = pattern.sub(repl, text)
    return text


# ------------------------------------------------------------ key helpers
def _sanitize(name: str) -> str:
    return re.sub(r"[^a-z0-9_.\-]", "_", name.strip().lower())[:48]


def sev_key(severity: str) -> str:
    return f"sev_{severity.strip().upper()}"


def svc_key(service: str) -> str:
    return f"svc_{_sanitize(service)}"


def code_key(code: str) -> str:
    return f"code_{_sanitize(code)}"


def to_epoch(dt: datetime) -> float:
    """Epoch seconds. Naive datetimes are interpreted as UTC (project convention)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


# ---------------------------------------------------------------- parsing
def _tz_offset(tz: Optional[str]) -> timedelta:
    if not tz or tz == "Z":
        return timedelta(0)
    sign = 1 if tz[0] == "+" else -1
    digits = tz[1:].replace(":", "")
    return sign * timedelta(hours=int(digits[:2]), minutes=int(digits[2:4]))


def _parse_timestamp(line: str) -> tuple[Optional[datetime], int]:
    """Return (naive-UTC datetime or None, end index of the timestamp text)."""
    head = line[:120]
    m = _APACHE_ERR_TS.match(head)
    if m:
        mon, day, hh, mm, ss, year = m.groups()
        try:
            return datetime(int(year), _MONTHS[mon], int(day), int(hh), int(mm), int(ss)), m.end()
        except (KeyError, ValueError):
            return None, 0
    m = _APACHE_ACC_TS.search(head)
    if m:
        day, mon, year, hh, mm, ss, tz = m.groups()
        try:
            dt = datetime(int(year), _MONTHS[mon], int(day), int(hh), int(mm), int(ss))
            return dt - _tz_offset(tz), m.end()
        except (KeyError, ValueError):
            return None, 0
    m = _ISO.search(head)
    if m:
        y, mo, d, hh, mi, ss, frac, tz = m.groups()
        try:
            dt = datetime(int(y), int(mo), int(d), int(hh), int(mi), int(ss),
                          int((frac or "0").ljust(6, "0")))
            return dt - _tz_offset(tz), m.end()
        except ValueError:
            return None, 0
    return None, 0


def _extract_error_codes(text: str) -> list[str]:
    found: list[str] = []
    for rx in (_ERRNO, _ERR_UNDERSCORE, _VENDOR_CODE, _EXC_NAME):
        for m in rx.finditer(text):
            if m.group(1) not in found:
                found.append(m.group(1))
    for rx in (_HTTP_ACCESS, _HTTP_KV):
        for m in rx.finditer(text):
            code = f"HTTP_{m.group(1)}"
            if code not in found:
                found.append(code)
    return found[:MAX_FLAGS_PER_CHUNK]


def parse_line(line: str) -> dict:
    """Extract only what is actually present in a single log line."""
    info = {"timestamp": None, "severity": None, "service": None,
            "request_id": None, "error_codes": []}
    ts, ts_end = _parse_timestamp(line)
    info["timestamp"] = ts
    rest = line[ts_end:] if ts else line

    sev_end = 0
    m = _SEV_BRACKET.search(rest[:80]) or _SEV_BARE.search(rest[:80])
    if m:
        info["severity"] = _SEV_ALIASES.get(m.group(1).upper())
        sev_end = m.end()

    tail = rest[sev_end:].lstrip(" \t-:")
    svc = None
    kv = _SERVICE_KV.search(line[:300])
    if kv:
        svc = kv.group(1)
    elif ts or m:
        for rx in (_SERVICE_BRACKET, _SERVICE_DOTTED, _SERVICE_COLON):
            sm = rx.match(tail)
            if sm:
                svc = sm.group(1)
                break
    if svc is None and not ts:
        sy = _SYSLOG.match(line)
        if sy:
            svc = sy.group(1)
    if svc and svc.lower() not in _SERVICE_STOP and not svc.lower().startswith("req-"):
        info["service"] = svc

    rid = _REQ_ID.search(line) or _REQ_ID_KV.search(line)
    if rid:
        info["request_id"] = rid.group(1)
    info["error_codes"] = _extract_error_codes(line[:MAX_LINE_CHARS])
    return info


# ----------------------------------------------------------------- events
@dataclass
class Event:
    seq: int
    line_start: int
    line_end: int
    text: str
    timestamp: Optional[datetime]
    severity: Optional[str]
    service: Optional[str]
    request_id: Optional[str]
    error_codes: list


def _iter_events(path: Path) -> Iterator[Event]:
    seq = 0
    cur: Optional[dict] = None
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.rstrip("\r\n")
            if not line.strip():
                continue
            if len(line) > MAX_LINE_CHARS:
                line = line[:MAX_LINE_CHARS] + " …[line truncated]"
            if cur is not None and _CONTINUATION.match(line):
                cur["lines"].append(line)
                cur["end"] = lineno
                for code in _extract_error_codes(line):
                    if code not in cur["codes"]:
                        cur["codes"].append(code)
                continue
            if cur is not None:
                yield _finish(cur)
            info = parse_line(line)
            seq += 1
            cur = {"seq": seq, "start": lineno, "end": lineno, "lines": [line],
                   "info": info, "codes": list(info["error_codes"])}
    if cur is not None:
        yield _finish(cur)


def _finish(cur: dict) -> Event:
    text = "\n".join(cur["lines"])
    if len(text) > settings.max_chunk_chars:
        text = text[: settings.max_chunk_chars] + "\n…[event truncated]"
    info = cur["info"]
    return Event(
        seq=cur["seq"], line_start=cur["start"], line_end=cur["end"], text=text,
        timestamp=info["timestamp"], severity=info["severity"],
        service=info["service"], request_id=info["request_id"],
        error_codes=cur["codes"][:MAX_FLAGS_PER_CHUNK],
    )


# ----------------------------------------------------------------- chunks
def make_chunk_id(job_id: str, index: int) -> str:
    """Stable ID: retries of the same job rewrite the same records."""
    return f"{job_id}:{index:06d}"


def _build_chunk(job_id: str, source_file: str, index: int, events: list[Event]) -> dict:
    meta: dict = {
        "job_id": job_id,
        "source_file": source_file,
        "chunk_index": index,
        "start_line": events[0].line_start,
        "end_line": events[-1].line_end,
        "event_count": len(events),
        "first_seq": events[0].seq,
        "last_seq": events[-1].seq,
    }
    stamps = [to_epoch(e.timestamp) for e in events if e.timestamp]
    if stamps:
        meta["ts_start"] = min(stamps)
        meta["ts_end"] = max(stamps)

    severities = {e.severity for e in events if e.severity}
    if severities:
        top = max(severities, key=lambda s: SEVERITY_RANK[s])
        meta["severity"] = top
        meta["severity_rank"] = SEVERITY_RANK[top]
        for s in severities:
            meta[sev_key(s)] = True

    services: list[str] = []
    codes: list[str] = []
    req_ids: list[str] = []
    for e in events:
        if e.service and e.service not in services:
            services.append(e.service)
        if e.request_id and e.request_id not in req_ids:
            req_ids.append(e.request_id)
        for c in e.error_codes:
            if c not in codes:
                codes.append(c)
    services, codes, req_ids = (
        services[:MAX_FLAGS_PER_CHUNK], codes[:MAX_FLAGS_PER_CHUNK], req_ids[:MAX_FLAGS_PER_CHUNK]
    )
    if services:
        meta["service"] = services[0]
        for s in services:
            meta[svc_key(s)] = True
    if codes:
        meta["error_code"] = codes[0]
        for c in codes:
            meta[code_key(c)] = True
    if req_ids:
        meta["request_id"] = req_ids[0]

    return {
        "id": make_chunk_id(job_id, index),
        "document": "\n".join(e.text for e in events),
        "metadata": meta,
    }


def iter_chunks(path: str | Path, job_id: str, source_file: Optional[str] = None,
                chunk_lines: Optional[int] = None,
                max_chars: Optional[int] = None) -> Iterator[dict]:
    """Stream a log file as chunks of ~chunk_lines lines on event boundaries.

    Yields dicts: {"id": str, "document": str, "metadata": dict}.
    """
    path = Path(path)
    source_file = source_file or path.name
    chunk_lines = chunk_lines or settings.chunk_lines
    max_chars = max_chars or settings.max_chunk_chars

    buf: list[Event] = []
    lines = chars = index = 0
    for ev in _iter_events(path):
        ev_lines = ev.line_end - ev.line_start + 1
        if buf and chars + len(ev.text) > max_chars:
            yield _build_chunk(job_id, source_file, index, buf)
            index += 1
            buf, lines, chars = [], 0, 0
        buf.append(ev)
        lines += ev_lines
        chars += len(ev.text)
        if lines >= chunk_lines:
            yield _build_chunk(job_id, source_file, index, buf)
            index += 1
            buf, lines, chars = [], 0, 0
    if buf:
        yield _build_chunk(job_id, source_file, index, buf)