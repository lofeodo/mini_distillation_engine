# pipeline/run_step1.py
from __future__ import annotations

from pathlib import Path

from .chunk import ChunkingConfig, chunk_lines
from .ingest import parse_guideline_lines
from .io_utils import write_json, chunks_to_dicts, records_to_dicts


def main() -> None:
    guideline_path = Path("data/guideline.txt")
    records = parse_guideline_lines(guideline_path)
    chunks = chunk_lines(records, ChunkingConfig(max_lines_per_chunk=20, max_chars_per_chunk=1200))

    write_json(Path("outputs/step1_lines.json"), records_to_dicts(records))
    write_json(Path("outputs/step1_chunks.json"), chunks_to_dicts(chunks))

    print(f"Parsed lines: {len(records)}")
    print(f"Chunks: {len(chunks)}")
    print("Wrote outputs/step1_lines.json and outputs/step1_chunks.json")


if __name__ == "__main__":
    main()
