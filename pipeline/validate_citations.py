# pipeline/validate_citations.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple, Any


class CitationValidationError(ValueError):
    pass


def build_chunk_index(chunks: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    idx: Dict[str, Dict[str, Any]] = {}
    for ch in chunks:
        cid = ch["chunk_id"]
        if cid in idx:
            raise CitationValidationError(f"Duplicate chunk_id in chunks: {cid}")
        idx[cid] = ch
    return idx


def validate_citation_bounds(
    chunk_index: Dict[str, Dict[str, Any]],
    citation: Dict[str, Any],
) -> None:
    cid = citation.get("chunk_id")
    ls = citation.get("line_start")
    le = citation.get("line_end")

    if cid not in chunk_index:
        raise CitationValidationError(f"Unknown chunk_id in citation: {cid}")

    ch = chunk_index[cid]
    ch_ls = ch["line_start"]
    ch_le = ch["line_end"]

    if not isinstance(ls, int) or not isinstance(le, int):
        raise CitationValidationError(f"Citation line_start/line_end must be int: {citation}")

    if ls > le:
        raise CitationValidationError(f"Invalid citation range (start > end): {citation}")

    if ls < ch_ls or le > ch_le:
        raise CitationValidationError(
            f"Citation out of bounds for {cid}: {ls}-{le} not within {ch_ls}-{ch_le}"
        )


def validate_citations(
    chunks: List[Dict[str, Any]],
    citations: Iterable[Dict[str, Any]],
) -> None:
    idx = build_chunk_index(chunks)
    for c in citations:
        validate_citation_bounds(idx, c)