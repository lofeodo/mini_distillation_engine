# pipeline/chunk.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from .contracts import Chunk, LineRecord


@dataclass(frozen=True)
class ChunkingConfig:
    """
    Deterministic chunking config.

    Rules (applied in order):
      1) Never exceed max_lines_per_chunk
      2) Try not to exceed max_chars_per_chunk (soft limit)
      3) Chunks are contiguous line ranges
    """
    max_lines_per_chunk: int = 20
    max_chars_per_chunk: int = 1200


def _format_line_for_chunk(r: LineRecord) -> str:
    # Include the original line number in the chunk text for human audit.
    # This is redundant (we already store ranges), but helps LLM + reviewer.
    return f"{r.line_no}. {r.text}".rstrip()


def chunk_lines(records: Sequence[LineRecord], cfg: ChunkingConfig = ChunkingConfig()) -> List[Chunk]:
    """
    Deterministically chunk parsed line records into contiguous blocks.

    Chunk IDs are assigned in encounter order: c0001, c0002, ...
    Determinism guarantee: given identical records + config, output is identical.
    """
    if cfg.max_lines_per_chunk <= 0:
        raise ValueError("max_lines_per_chunk must be > 0")
    if cfg.max_chars_per_chunk <= 0:
        raise ValueError("max_chars_per_chunk must be > 0")

    chunks: List[Chunk] = []
    cur: List[LineRecord] = []
    cur_chars = 0

    def flush():
        nonlocal cur, cur_chars, chunks
        if not cur:
            return
        chunk_index = len(chunks) + 1
        chunk_id = f"c{chunk_index:04d}"
        line_start = cur[0].line_no
        line_end = cur[-1].line_no
        text_lines = [_format_line_for_chunk(r) for r in cur]
        text = "\n".join(text_lines)
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                line_start=line_start,
                line_end=line_end,
                text=text,
                lines=tuple(cur),
            )
        )
        cur = []
        cur_chars = 0

    for r in records:
        line_str = _format_line_for_chunk(r)
        add_len = len(line_str) + 1  # + newline

        # Hard rule: max lines per chunk
        would_exceed_lines = (len(cur) + 1) > cfg.max_lines_per_chunk

        # Soft rule: max chars (only split if we already have something)
        would_exceed_chars = (cur_chars + add_len) > cfg.max_chars_per_chunk and len(cur) > 0

        if would_exceed_lines or would_exceed_chars:
            flush()

        cur.append(r)
        cur_chars += add_len

    flush()
    return chunks