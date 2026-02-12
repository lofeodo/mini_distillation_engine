# pipeline/run_step8.py
from __future__ import annotations

from pipeline.io_utils import read_json, write_json
from schemas.schemas_workflow import Workflow
from pipeline.render_workflow_md import render_workflow_markdown


IN_PATH = "outputs/step7_workflow.json"
OUT_MD = "outputs/step8_workflow_audit.md"


def main():
    raw = read_json(IN_PATH)
    wf = Workflow.model_validate(raw)

    md = render_workflow_markdown(wf)

    # write as plain text
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"[OK] Wrote: {OUT_MD}")


if __name__ == "__main__":
    main()