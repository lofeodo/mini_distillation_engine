# pipeline/run_step6.py
from __future__ import annotations

from pipeline.io_utils import read_json, write_json
from schemas.schemas_extraction import ExtractionOutput
from pipeline.normalize import normalize_and_canonicalize, NormalizeConfig
from pipeline.validate_citations import validate_citations


IN_PATH = "outputs/step5_extraction_output.json"
CHUNKS_PATH = "outputs/step1_chunks.json"
LINES_PATH = "outputs/step1_lines.json"
OUT_PATH = "outputs/step6_extraction_output_clean.json"


def main():
    raw = read_json(IN_PATH)
    extraction = ExtractionOutput.model_validate(raw)

    chunks = read_json(CHUNKS_PATH)
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("outputs/step1_chunks.json must be a non-empty list")

    lines = read_json(LINES_PATH)
    if not isinstance(lines, list) or not lines:
        raise ValueError("outputs/step1_lines.json must be a non-empty list")

    line_text_by_no = {int(x["line_no"]): x["text"] for x in lines}

    cleaned, step6_warnings = normalize_and_canonicalize(
        extraction,
        cfg=NormalizeConfig(
            min_chars=10,
            fuzzy_threshold=0.94,
            max_fuzzy_comp_per_type=8000,
            citation_tighten_max_window=4,
        ),
        line_text_by_no=line_text_by_no,
    )

    # Flatten citations into list[dict] for validate_citations(chunks, citations)
    flat_citations = []
    for f in cleaned.extracted_facts:
        for c in f.citations:
            flat_citations.append(
                {"chunk_id": c.chunk_id, "line_start": c.line_start, "line_end": c.line_end}
            )

    validate_citations(chunks, flat_citations)

    # Final schema round-trip check (fail closed)
    ExtractionOutput.model_validate(cleaned.model_dump())

    write_json(OUT_PATH, cleaned.model_dump(mode="json"))
    print(f"[OK] Wrote: {OUT_PATH}")

    if step6_warnings:
        print("\nStep 6 Warnings:")
        for w in step6_warnings:
            print(f" - {w}")


if __name__ == "__main__":
    main()