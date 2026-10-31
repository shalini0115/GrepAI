import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import main
from app.ingestion import iter_chunks, parse_line
from app.retrieval import build_where
from app.schemas import QueryFilters


def test_parse_app_line():
    i = parse_line("2026-10-27 03:00:05 ERROR [database-service] Connection timeout request_id=req-103")
    assert i["severity"] == "ERROR" and i["service"] == "database-service"
    assert i["request_id"] == "req-103" and i["timestamp"].year == 2026


def test_syslog_has_no_invented_timestamp():
    assert parse_line("Jun  9 06:06:20 combo syslogd 1.4.1: restart.")["timestamp"] is None


def test_unknown_format_yields_nothing():
    i = parse_line("???")
    assert i["timestamp"] is None and i["severity"] is None and i["service"] is None


def test_multiline_exception_kept(tmp_path):
    p = tmp_path / "t.log"
    p.write_text('2026-01-01 00:00:00 ERROR [a] boom\nTraceback (most recent call last):\n  File "x", line 1\nValueError: bad\n2026-01-01 00:00:01 INFO [a] ok\n')
    chunks = list(iter_chunks(p, "j"))
    assert "ValueError: bad" in chunks[0]["document"] and chunks[0]["metadata"]["sev_ERROR"] is True


def test_chunk_boundaries_and_stable_ids(tmp_path):
    p = tmp_path / "t.log"
    p.write_text("".join(f"2026-01-01 00:00:{i % 60:02d} INFO [a] m{i}\n" for i in range(120)))
    a, b = list(iter_chunks(p, "j", chunk_lines=50)), list(iter_chunks(p, "j", chunk_lines=50))
    assert [c["id"] for c in a] == [c["id"] for c in b] == ["j:000000", "j:000001", "j:000002"]
    assert [c["metadata"]["event_count"] for c in a] == [50, 50, 20]


def test_build_where():
    assert build_where(QueryFilters()) is None
    assert build_where(QueryFilters(severity=["ERROR"])) == {"sev_ERROR": True}
    w = build_where(QueryFilters(severity=["ERROR", "WARN"], start_time="2026-01-01T00:00:00"))
    assert "$and" in w and {"$or": [{"sev_ERROR": True}, {"sev_WARNING": True}]} in w["$and"]


def test_schema_validation():
    with pytest.raises(ValidationError):
        QueryFilters(severity=["bogus"])
    with pytest.raises(ValidationError):
        QueryFilters(start_time="2026-01-02T00:00:00", end_time="2026-01-01T00:00:00")


@pytest.fixture
def client(tmp_path, monkeypatch):
    s = main.settings
    old = (s.upload_dir, s.max_upload_bytes)
    object.__setattr__(s, "upload_dir", tmp_path)
    object.__setattr__(s, "max_upload_bytes", 200)
    monkeypatch.setattr(main.storage, "create_job", lambda *a, **k: None)
    monkeypatch.setattr(main.storage, "update_job", lambda *a, **k: None)
    monkeypatch.setattr(main, "dispatch_ingestion", lambda *a, **k: None)
    yield TestClient(main.app), tmp_path
    object.__setattr__(s, "upload_dir", old[0])
    object.__setattr__(s, "max_upload_bytes", old[1])


def _up(c, name, data):
    return c.post("/api/v1/ingestion", files={"file": (name, data)})


def test_upload_ok(client):
    c, d = client
    r = _up(c, "a.log", b"2026-01-01 00:00:00 INFO [a] hi\n")
    assert r.status_code == 202 and len(list(d.glob("*.log"))) == 1


def test_upload_rejections(client):
    c, d = client
    assert _up(c, "a.log", b"").status_code == 400
    assert _up(c, "a.txt", b"x").status_code == 415
    assert _up(c, "a.log", b"x" * 500).status_code == 413
    assert list(d.glob("*.log")) == []


def test_dispatch_failure_cleans_up(client, monkeypatch):
    c, d = client

    def boom(*a, **k):
        raise ConnectionError("down")

    monkeypatch.setattr(main, "dispatch_ingestion", boom)
    assert _up(c, "a.log", b"2026-01-01 00:00:00 INFO [a] hi\n").status_code == 503
    assert list(d.glob("*.log")) == []


def test_status_404_and_bad_id(client, monkeypatch):
    c, _ = client
    monkeypatch.setattr(main.storage, "get_job", lambda j: None)
    assert c.get("/api/v1/ingestion/" + "a" * 32).status_code == 404
    assert c.get("/api/v1/ingestion/not-a-job").status_code == 422


def test_invalid_filter_and_no_evidence(client, monkeypatch):
    c, _ = client
    assert c.post("/api/v1/query", json={"question": "why", "filters": {"severity": ["x"]}}).status_code == 422
    monkeypatch.setattr(main.storage, "query_chunks", lambda *a, **k: [])
    r = c.post("/api/v1/query", json={"question": "why did it fail", "filters": {"job_id": "nope"}})
    assert r.status_code == 200 and r.json()["confidence"] == "undetermined"
    assert r.json()["filters_applied"]["candidates_matched"] == 0