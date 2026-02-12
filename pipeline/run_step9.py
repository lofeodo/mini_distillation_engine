# pipeline/run_step9.py
from __future__ import annotations

from pipeline.io_utils import read_json
from schemas.schemas_workflow import Workflow
from pipeline.render_clinical_summary import render_clinical_summary


IN_WORKFLOW = "outputs/step7_workflow.json"
IN_LINES = "outputs/step1_lines.json"
OUT_MD = "outputs/step9_clinical_summary.md"


def main():
    wf_raw = read_json(IN_WORKFLOW)
    wf = Workflow.model_validate(wf_raw)

    lines = read_json(IN_LINES)  # list[{line_no, text}]
    line_text_by_no = {int(x["line_no"]): x["text"] for x in lines}

    md = render_clinical_summary(wf, line_text_by_no=line_text_by_no)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"[OK] Wrote: {OUT_MD}")


if __name__ == "__main__":
    main()