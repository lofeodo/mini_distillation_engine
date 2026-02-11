# pipeline/run_step2.py
from __future__ import annotations

import json
from pathlib import Path

from pipeline.schemas_extraction import ExtractionOutput
from pipeline.schemas_workflow import Workflow
from pipeline.validate_citations import validate_citations
from pipeline.validate_workflow import validate_workflow_graph


ROOT = Path(__file__).resolve().parents[1]
CHUNKS_PATH = ROOT / "outputs" / "step1_chunks.json"


def load_chunks():
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    if not isinstance(chunks, list):
        raise ValueError("step1_chunks.json must be a list")
    return chunks


def main():
    chunks = load_chunks()

    # Minimal example payloads (you’ll replace these with LLM outputs later)
    extraction_payload = {
        "guideline_id": "inesss_hypertension_demo",
        "model_id": "local-placeholder",
        "chunking": {"max_lines": 20, "soft_char_limit": 1200},
        "extracted_facts": [
            {
                "fact_id": "f0001",
                "fact_type": "other",
                "statement": "Example placeholder fact (replace with real extraction).",
                "strength": "unclear",
                "requires_human_review": True,
                "citations": [
                    {"chunk_id": chunks[0]["chunk_id"], "line_start": chunks[0]["line_start"], "line_end": chunks[0]["line_start"]}
                ],
            }
        ],
        "warnings": ["This is a Step 2 placeholder payload."],
        "meta": {"offline": True},
    }

    extraction = ExtractionOutput.model_validate(extraction_payload)

    # Validate all citations in extraction facts against chunk bounds
    all_fact_citations = []
    for f in extraction.extracted_facts:
        all_fact_citations.extend([c.model_dump() for c in f.citations])
    validate_citations(chunks, all_fact_citations)

    workflow_payload = {
        "workflow_id": "wf0001",
        "guideline_id": extraction.guideline_id,
        "inputs": [
            {"input_id": "in001", "name": "example_boolean", "type": "bool", "description": "Placeholder input."}
        ],
        "nodes": [
            {
                "node_id": "d0001",
                "node_type": "decision",
                "condition": "in001 == true",
                "true_next": "a0001",
                "false_next": "e0001",
                "citations": all_fact_citations,
            },
            {
                "node_id": "a0001",
                "node_type": "action",
                "action": "Example action (replace with synthesized action).",
                "requires_human_review": True,
                "citations": all_fact_citations,
            },
            {"node_id": "e0001", "node_type": "end", "label": "Stop"},
        ],
        "start_node_id": "d0001",
        "requires_human_review": True,
        "warnings": ["Step 2 placeholder workflow."],
        "meta": {"offline": True},
    }

    workflow = Workflow.model_validate(workflow_payload)

    # Validate citations on workflow nodes too
    wf_citations = []
    for node in workflow.nodes:
        if hasattr(node, "citations"):
            wf_citations.extend([c.model_dump() for c in node.citations])
    validate_citations(chunks, wf_citations)

    # Validate graph integrity (ids, reachability, edges)
    validate_workflow_graph(workflow)

    print("✅ Step 2 passed: schemas + citations + workflow graph validation")


if __name__ == "__main__":
    main()