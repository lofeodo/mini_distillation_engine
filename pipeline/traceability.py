# pipeline/traceability.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Iterable

from .io_utils import read_json


@dataclass(frozen=True)
class Citation:
    chunk_id: str
    line_start: int
    line_end: int


class TraceabilityError(ValueError):
    """Fail-closed traceability error."""


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise TraceabilityError(msg)


def build_trace_index(
    lines_path: str = "outputs/step1_lines.json",
    chunks_path: str = "outputs/step1_chunks.json",
) -> Dict[str, Any]:
    """
    Builds canonical, deterministic trace index from Step 1 artifacts.
    - line_text: {line_no -> text}
    - chunk_bounds: {chunk_id -> (line_start, line_end)}
    """
    lines = read_json(lines_path)
    chunks = read_json(chunks_path)

    _require(isinstance(lines, list) and len(lines) > 0, "step1_lines.json must be a non-empty list.")
    _require(isinstance(chunks, list) and len(chunks) > 0, "step1_chunks.json must be a non-empty list.")

    line_text: Dict[int, str] = {}
    for rec in lines:
        _require(isinstance(rec, dict), "Each line record must be an object.")
        _require("line_no" in rec and "text" in rec, "Each line record must contain line_no and text.")
        ln = rec["line_no"]
        tx = rec["text"]
        _require(isinstance(ln, int), "line_no must be int.")
        _require(isinstance(tx, str), "text must be str.")
        _require(ln not in line_text, f"Duplicate line_no in lines: {ln}")
        line_text[ln] = tx

    chunk_bounds: Dict[str, Tuple[int, int]] = {}
    for ch in chunks:
        _require(isinstance(ch, dict), "Each chunk must be an object.")
        for k in ("chunk_id", "line_start", "line_end", "text"):
            _require(k in ch, f"Chunk missing key: {k}")
        cid = ch["chunk_id"]
        ls = ch["line_start"]
        le = ch["line_end"]
        _require(isinstance(cid, str), "chunk_id must be str.")
        _require(isinstance(ls, int) and isinstance(le, int), "chunk line_start/line_end must be int.")
        _require(ls <= le, f"Chunk {cid} has invalid bounds: {ls}..{le}")
        _require(cid not in chunk_bounds, f"Duplicate chunk_id in chunks: {cid}")
        chunk_bounds[cid] = (ls, le)

    # Sanity: chunk bounds must reference known lines
    min_line = min(line_text.keys())
    max_line = max(line_text.keys())
    for cid, (ls, le) in chunk_bounds.items():
        _require(min_line <= ls <= max_line, f"Chunk {cid} line_start out of range: {ls}")
        _require(min_line <= le <= max_line, f"Chunk {cid} line_end out of range: {le}")

    return {
        "line_text": line_text,
        "chunk_bounds": chunk_bounds,
        "meta": {
            "min_line": min_line,
            "max_line": max_line,
            "num_lines": len(line_text),
            "num_chunks": len(chunk_bounds),
        },
    }


def validate_citation(index: Dict[str, Any], cit: Citation) -> None:
    bounds = index["chunk_bounds"]
    _require(cit.chunk_id in bounds, f"Unknown chunk_id: {cit.chunk_id}")

    ls, le = bounds[cit.chunk_id]
    _require(isinstance(cit.line_start, int) and isinstance(cit.line_end, int), "Citation lines must be int.")
    _require(cit.line_start <= cit.line_end, "Citation line_start must be <= line_end.")
    _require(ls <= cit.line_start <= le, f"Citation line_start out of chunk bounds: {cit.chunk_id} {cit.line_start} not in {ls}..{le}")
    _require(ls <= cit.line_end <= le, f"Citation line_end out of chunk bounds: {cit.chunk_id} {cit.line_end} not in {ls}..{le}")


def extract_cited_lines(index: Dict[str, Any], cit: Citation) -> List[Tuple[int, str]]:
    """
    Returns exact cited lines [(line_no, text), ...] deterministically.
    """
    validate_citation(index, cit)
    line_text: Dict[int, str] = index["line_text"]

    out: List[Tuple[int, str]] = []
    for ln in range(cit.line_start, cit.line_end + 1):
        _require(ln in line_text, f"Missing line in canonical source: {ln}")
        out.append((ln, line_text[ln]))
    return out


def format_audit_snippet(index: Dict[str, Any], cit: Citation) -> str:
    """
    Deterministic snippet with stable formatting for audit logs / markdown previews.
    """
    lines = extract_cited_lines(index, cit)
    header = f"[{cit.chunk_id}:{cit.line_start}-{cit.line_end}]"
    body = "\n".join(f"{ln:04d}: {tx}" for ln, tx in lines)
    return f"{header}\n{body}"


def validate_citations_list(index: Dict[str, Any], citations: Iterable[Dict[str, Any]]) -> List[Citation]:
    """
    Accepts list of dict citations (e.g., from LLM JSON) and returns parsed Citation objects.
    Fail-closed on any structural issue.
    """
    _require(isinstance(citations, list), "citations must be a list.")
    parsed: List[Citation] = []
    seen = set()

    for c in citations:
        _require(isinstance(c, dict), "Each citation must be an object.")
        for k in ("chunk_id", "line_start", "line_end"):
            _require(k in c, f"Citation missing key: {k}")

        cit = Citation(
            chunk_id=c["chunk_id"],
            line_start=c["line_start"],
            line_end=c["line_end"],
        )

        # basic type checks
        _require(isinstance(cit.chunk_id, str), "citation.chunk_id must be str.")
        _require(isinstance(cit.line_start, int), "citation.line_start must be int.")
        _require(isinstance(cit.line_end, int), "citation.line_end must be int.")

        # reject duplicates exactly (chunk_id, start, end)
        key = (cit.chunk_id, cit.line_start, cit.line_end)
        _require(key not in seen, f"Duplicate citation entry: {key}")
        seen.add(key)

        # bounds check
        validate_citation(index, cit)
        parsed.append(cit)

    return parsed