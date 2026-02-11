# pipeline/io_utils.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .contracts import Chunk, LineRecord


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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
