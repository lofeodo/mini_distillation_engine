# pipeline/run_step3.py
from __future__ import annotations

from typing import Dict, Any

from .io_utils import write_json
from .traceability import (
    build_trace_index,
    Citation,
    format_audit_snippet,
)


def _make_smoketest(index: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic smoke-test: pick first chunk and cite its first 2 lines (or fewer).
    """
    chunk_bounds = index["chunk_bounds"]
    # chunks are c0001, c0002, ... so lexical sort is stable
    first_chunk_id = sorted(chunk_bounds.keys())[0]
    ls, le = chunk_bounds[first_chunk_id]
    end = min(ls + 1, le)  # first 1-2 lines deterministically

    cit = Citation(chunk_id=first_chunk_id, line_start=ls, line_end=end)
    snippet = format_audit_snippet(index, cit)

    return {
        "citation": {
            "chunk_id": cit.chunk_id,
            "line_start": cit.line_start,
            "line_end": cit.line_end,
        },
        "snippet": snippet,
    }


def main() -> None:
    index = build_trace_index()

    # Write a lightweight JSON-serializable index (convert keys to strings where needed)
    serializable = {
        "meta": index["meta"],
        "chunk_bounds": {cid: {"line_start": ls, "line_end": le} for cid, (ls, le) in index["chunk_bounds"].items()},
        # Keep line_text out of the index file to avoid huge output; we can always re-derive from step1_lines.json
        "derived_from": {
            "lines_path": "outputs/step1_lines.json",
            "chunks_path": "outputs/step1_chunks.json",
        },
    }
    write_json("outputs/step3_citation_index.json", serializable)

    smoketest = _make_smoketest(index)
    write_json("outputs/step3_citation_smoketest.json", smoketest)

    # Also write a simple markdown snippet preview deterministically
    md = "# Step 3 — Citation Smoke Test Snippet\n\n"
    md += "```text\n" + smoketest["snippet"] + "\n```\n"
    with open("outputs/step3_citation_snippets.md", "w", encoding="utf-8") as f:
        f.write(md)

    print("✅ Step 3 complete.")
    print("Wrote:")
    print(" - outputs/step3_citation_index.json")
    print(" - outputs/step3_citation_smoketest.json")
    print(" - outputs/step3_citation_snippets.md")


if __name__ == "__main__":
    main()