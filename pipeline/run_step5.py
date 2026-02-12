# pipeline/run_step5.py
from __future__ import annotations

from .extract import run_extraction
from .io_utils import write_json


def main() -> None:
    model_id = "microsoft/Phi-3-mini-4k-instruct"
    guideline_id = "inesss_hypertension"

    extraction_output = run_extraction(
        model_id=model_id,
        guideline_id=guideline_id,
        chunks_path="outputs/step1_chunks.json",
    )

    write_json("outputs/step5_extraction_output.json", extraction_output)

    print("✅ Step 5 complete.")
    print("Wrote: outputs/step5_extraction_output.json")


if __name__ == "__main__":
    main()