# pipeline/contracts.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


# ---- Canonical identifiers ----
# Guideline source is chunked into stable "chunk_id" values.
# Chunk IDs must be stable across runs given the same input and chunking config.
# Format: c0001, c0002, ...
ChunkId = str


@dataclass(frozen=True)
class LineRecord:
    """A single line from the guideline, with deterministic line_no and raw text."""
    line_no: int
    text: str


@dataclass(frozen=True)
class Chunk:
    """A deterministic chunk built from contiguous guideline lines."""
    chunk_id: ChunkId
    line_start: int
    line_end: int
    text: str  # joined chunk text (includes original line numbers for readability)
    lines: Sequence[LineRecord]


@dataclass(frozen=True)
class Citation:
    """
    Canonical citation contract used everywhere (extraction + workflow).

    - chunk_id: must exist in the produced chunks
    - line_start/line_end: must be within the chunk's [line_start, line_end] range
    - quote: optional short quote for human audit (never required for validation)
    """
    chunk_id: ChunkId
    line_start: int
    line_end: int
    quote: Optional[str] = None