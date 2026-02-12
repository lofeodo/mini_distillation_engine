# pipeline/render_workflow_md.py
from __future__ import annotations

from typing import Any, Dict, List

from schemas.schemas_workflow import Workflow
from pipeline.traceability import build_trace_index, format_audit_snippet


def _md_escape(s: str) -> str:
    return s.replace("\n", " ").strip()


def _render_inputs(inputs: List[Dict[str, Any]]) -> str:
    lines = ["## Inputs", ""]
    for inp in inputs:
        desc = inp.get("description") or ""
        lines.append(f"- **{inp['input_id']}** `{inp['name']}` ({inp['type']}): {_md_escape(desc)}")
    lines.append("")
    return "\n".join(lines)


def _render_citations(index: Dict[str, Any], citations: List[Dict[str, Any]], max_snippets: int = 12) -> str:
    if not citations:
        return "_No citations._"

    out: List[str] = []
    out.append(f"_Citations: {len(citations)}_")
    out.append("")
    for i, c in enumerate(citations[:max_snippets], start=1):
        # format_audit_snippet expects a traceability.Citation dataclass, but we can pass dict -> construct on fly
        snippet = format_audit_snippet(
            index,
            cit=type("TmpCit", (), {
                "chunk_id": c["chunk_id"],
                "line_start": c["line_start"],
                "line_end": c["line_end"],
            })()
        )
        out.append(f"**[{i}]** `{c['chunk_id']}:{c['line_start']}-{c['line_end']}`")
        out.append("")
        out.append("```text")
        out.append(snippet)
        out.append("```")
        out.append("")
    if len(citations) > max_snippets:
        out.append(f"_Showing first {max_snippets} citations (deterministic cap). Full citations remain in JSON._")
        out.append("")
    return "\n".join(out)


def render_workflow_markdown(
    wf: Workflow,
    lines_path: str = "outputs/step1_lines.json",
    chunks_path: str = "outputs/step1_chunks.json",
) -> str:
    index = build_trace_index(lines_path=lines_path, chunks_path=chunks_path)

    md: List[str] = []
    md.append(f"# Workflow Audit Preview — `{wf.workflow_id}`")
    md.append("")
    md.append(f"- guideline_id: `{wf.guideline_id}`")
    md.append(f"- start_node_id: `{wf.start_node_id}`")
    md.append(f"- requires_human_review: `{wf.requires_human_review}`")
    md.append("")

    if wf.warnings:
        md.append("## Warnings")
        md.append("")
        for w in wf.warnings:
            md.append(f"- {w}")
        md.append("")

    md.append(_render_inputs([i.model_dump(mode='json') for i in wf.inputs]))

    md.append("## Nodes")
    md.append("")

    # Deterministic order: nodes sorted by node_id
    nodes = sorted([n.model_dump(mode="json") for n in wf.nodes], key=lambda x: x["node_id"])

    for n in nodes:
        nid = n["node_id"]
        ntype = n["node_type"]

        md.append(f"### `{nid}` ({ntype})")
        md.append("")

        if ntype == "decision":
            md.append(f"- condition: `{_md_escape(n.get('condition',''))}`")
            md.append(f"- true_next: `{n.get('true_next')}`")
            md.append(f"- false_next: `{n.get('false_next')}`")
            md.append("")
            md.append(_render_citations(index, n.get("citations") or []))

        elif ntype == "action":
            md.append(f"- action: {_md_escape(n.get('action',''))}")
            md.append(f"- requires_human_review: `{n.get('requires_human_review')}`")
            md.append("")
            md.append(_render_citations(index, n.get("citations") or []))

        elif ntype == "end":
            md.append(f"- label: {_md_escape(n.get('label',''))}")
            md.append("")
            # end nodes in your schema may not carry citations; keep consistent
            if "citations" in n:
                md.append(_render_citations(index, n.get("citations") or []))
            else:
                md.append("_No citations._")

        else:
            md.append("_Unknown node type._")

        md.append("")

    return "\n".join(md)