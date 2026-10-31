"""Service graph built from stored chunks. Nothing is invented.

Nodes are services seen in the log. Links come from consecutive events that
share a request_id. If the log has no request IDs, links fall back to
consecutive events in file order, and the response says so (edge_basis).
"""
from collections import defaultdict
from typing import Optional

from app import storage
from app.ingestion import SEVERITY_RANK, parse_line

MAX_CHUNKS = 3000
MAX_NODES = 40
MAX_EDGES = 120
MAX_SEQ = 300000
BAD = ("ERROR", "CRITICAL")


def _worse(a: Optional[str], b: Optional[str]) -> Optional[str]:
    return a if SEVERITY_RANK.get(a, -1) >= SEVERITY_RANK.get(b, -1) else b


def build_graph(job_id: str, highlight: Optional[list[str]] = None) -> dict:
    chunks = storage.get_job_chunks(job_id, MAX_CHUNKS)
    hot_ids = set(highlight or [])
    nodes: dict[str, dict] = {}
    by_req: dict[str, list[tuple]] = defaultdict(list)
    seq: list[tuple] = []
    events = 0

    for c in chunks:
        hot = c["id"] in hot_ids
        for line in c["document"].split("\n"):
            if not line or line[0] in " \t":
                continue
            info = parse_line(line)
            svc = info["service"]
            if not svc:
                continue
            events += 1
            sev = info["severity"]
            n = nodes.setdefault(svc, {"id": svc, "count": 0, "errors": 0,
                                       "warnings": 0, "severity": None, "hot": False})
            n["count"] += 1
            if sev in BAD:
                n["errors"] += 1
            elif sev == "WARNING":
                n["warnings"] += 1
            n["severity"] = _worse(n["severity"], sev)
            n["hot"] = n["hot"] or hot
            item = (svc, sev, hot)
            if info["request_id"]:
                by_req[info["request_id"]].append(item)
            if len(seq) < MAX_SEQ:
                seq.append(item)

    edges: dict[tuple, dict] = {}

    def link(a: tuple, b: tuple, rid: Optional[str] = None) -> None:
        (s1, v1, h1), (s2, v2, h2) = a, b
        if s1 == s2:
            return
        e = edges.setdefault((s1, s2), {"source": s1, "target": s2, "count": 0, "errors": 0,
                                        "severity": None, "hot": False, "samples": []})
        e["count"] += 1
        if v2 in BAD:
            e["errors"] += 1
        e["severity"] = _worse(e["severity"], _worse(v1, v2))
        e["hot"] = e["hot"] or (h1 and h2)
        if rid and rid not in e["samples"] and len(e["samples"]) < 3:
            e["samples"].append(rid)

    for rid, evs in by_req.items():
        for a, b in zip(evs, evs[1:]):
            link(a, b, rid)
    basis = "request_id"
    if not edges:
        basis = "sequence"
        for a, b in zip(seq, seq[1:]):
            link(a, b)
    if not edges:
        basis = "none"

    kept = sorted(nodes.values(), key=lambda n: -n["count"])[:MAX_NODES]
    ids = {n["id"] for n in kept}
    kept_edges = sorted(
        (e for e in edges.values() if e["source"] in ids and e["target"] in ids),
        key=lambda e: -e["count"],
    )[:MAX_EDGES]
    return {
        "nodes": kept,
        "edges": kept_edges,
        "stats": {"chunks": len(chunks), "events": events, "edge_basis": basis,
                  "truncated": len(chunks) >= MAX_CHUNKS or len(nodes) > MAX_NODES},
    }