# pipeline/run_step7.py
from __future__ import annotations

from pipeline.io_utils import read_json, write_json
from schemas.schemas_extraction import ExtractionOutput
from schemas.schemas_workflow import Workflow
from pipeline.synthesize_workflow import synthesize_workflow
from pipeline.validate_workflow import validate_workflow_graph


IN_PATH = "outputs/step6_extraction_output_clean.json"
OUT_PATH = "outputs/step7_workflow.json"


def main():
    raw = read_json(IN_PATH)
    ex = ExtractionOutput.model_validate(raw)

    wf = synthesize_workflow(ex)

    # Fail-closed workflow validation
    validate_workflow_graph(wf)

    # Schema round-trip check
    Workflow.model_validate(wf.model_dump())

    write_json(OUT_PATH, wf.model_dump(mode="json"))
    print(f"[OK] Wrote: {OUT_PATH}")


if __name__ == "__main__":
    main()