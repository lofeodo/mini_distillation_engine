# pipeline/ingest.py
from __future__ import annotations

import re
from pathlib import Path
from typing import List

from .contracts import LineRecord


_LINE_PATTERNS = [
    # "12. Some text"
    re.compile(r"^\s*(\d+)\.\s*(.*)\s*$"),
    # "12) Some text"
    re.compile(r"^\s*(\d+)\)\s*(.*)\s*$"),
    # "12 - Some text"
    re.compile(r"^\s*(\d+)\s*-\s*(.*)\s*$"),
    # "12\tSome text" or "12 Some text"
    re.compile(r"^\s*(\d+)\s+(.+?)\s*$"),
]


def parse_guideline_lines(guideline_path: Path) -> List[LineRecord]:
    """
    Deterministically parse a guideline text file that includes explicit line numbers.

    Fails closed if:
      - a non-empty line cannot be parsed into (line_no, text)
      - line numbers are not strictly increasing by 1
      - duplicate line numbers appear
    """
    raw = guideline_path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    records: List[LineRecord] = []
    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()

        # allow blank lines, but preserve them as explicit text if numbered;
        # if blank and unnumbered, skip to avoid shifting numbering.
        if stripped == "":
            continue

        parsed = None
        for pat in _LINE_PATTERNS:
            m = pat.match(raw_line)
            if m:
                line_no = int(m.group(1))
                text = (m.group(2) or "").strip()
                parsed = (line_no, text)
                break

        if parsed is None:
            raise ValueError(
                f"Unparseable guideline line at file line {idx}: {raw_line!r}\n"
                "Expected formats like '12. text', '12) text', '12 - text', or '12 text'."
            )

        records.append(LineRecord(line_no=parsed[0], text=parsed[1]))

    if not records:
        raise ValueError("Guideline appears empty or contains no parseable numbered lines.")

    # Fail-closed: enforce strict monotonic + contiguous numbering
    expected = records[0].line_no
    seen = set()
    for r in records:
        if r.line_no in seen:
            raise ValueError(f"Duplicate line number detected: {r.line_no}")
        seen.add(r.line_no)

        if r.line_no != expected:
            raise ValueError(
                f"Non-contiguous line numbering. Expected {expected}, got {r.line_no}.\n"
                "Fix guideline.txt so line numbers are strictly increasing by 1."
            )
        expected += 1

    return records