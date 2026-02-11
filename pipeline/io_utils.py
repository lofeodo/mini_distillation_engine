# pipeline/io_utils.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Union

from .contracts import Chunk, LineRecord


# Backward-compatible: still works when callers pass Path.
# Also allows passing a str without breaking anything.
PathLike = Union[str, Path]


def read_json(path: PathLike) -> Any:
    """
    Deterministic JSON reader (fail-closed).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"JSON file not found: {p}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {p}: {e}") from e


def write_json(path: PathLike, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def records_to_dicts(records: List[LineRecord]) -> List[Dict[str, Any]]:
    return [{"line_no": r.line_no, "text": r.text} for r in records]


def chunks_to_dicts(chunks: List[Chunk]) -> List[Dict[str, Any]]:
    return [
        {
            "chunk_id": c.chunk_id,
            "line_start": c.line_start,
            "line_end": c.line_end,
            "text": c.text,
        }
        for c in chunks
    ]