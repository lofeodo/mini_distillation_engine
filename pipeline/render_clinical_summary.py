# pipeline/render_clinical_summary.py
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


# -------------------- schema-tolerant getters --------------------

def _node_id(n: Any) -> str:
    return getattr(n, "node_id", None) or getattr(n, "id", None) or "unknown"


def _node_kind(n: Any) -> str:
    return (
        getattr(n, "kind", None)
        or getattr(n, "node_type", None)
        or getattr(n, "type", None)
        or "unknown"
    )


def _citations(n: Any) -> List[Any]:
    return list(getattr(n, "citations", []) or [])


def _cit_dump(c: Any) -> dict:
    return c.model_dump() if hasattr(c, "model_dump") else dict(c)


def _fmt_citation(c: Any) -> str:
    d = _cit_dump(c)
    chunk_id = d.get("chunk_id", "c????")
    line_start = d.get("line_start", "?")
    line_end = d.get("line_end", "?")
    return f"`{chunk_id}:{line_start}-{line_end}`"


def _action_text(a: Any) -> str:
    return getattr(a, "action", None) or getattr(a, "text", None) or "Action."


def _end_label(e: Any) -> str:
    return getattr(e, "label", None) or getattr(e, "text", None) or "End."


def _input_dump(inp: Any) -> dict:
    return inp.model_dump() if hasattr(inp, "model_dump") else dict(inp)


# -------------------- parsing / labeling --------------------

_COND_RE = re.compile(r"^\s*(in\d+)\s*==\s*(true|false)\s*$", re.IGNORECASE)


def _parse_condition(cond: str) -> Optional[Tuple[str, bool]]:
    m = _COND_RE.match(cond or "")
    if not m:
        return None
    return m.group(1), (m.group(2).lower() == "true")


def _friendly_gate_title(input_name: str, fallback_idx: int) -> str:
    name = (input_name or "").lower()
    if "population" in name or "eligible" in name:
        return "Eligibility"
    if "exclusion" in name or "contra" in name:
        return "Exclusions / Contraindications"
    if "red" in name or "flag" in name or "urgent" in name:
        return "Red Flags / Escalation"
    return f"Gate {fallback_idx}"


def _describe_next(node: Any) -> str:
    kind = _node_kind(node)
    if kind == "decision":
        return "Continue to next step."
    if kind == "action":
        return _action_text(node)
    if kind == "end":
        return _end_label(node)
    return "Continue."


def _pick_next_decision(node_map: Dict[str, Any], a: str, b: str) -> Optional[str]:
    na = node_map.get(a)
    nb = node_map.get(b)
    if na is not None and _node_kind(na) == "decision":
        return a
    if nb is not None and _node_kind(nb) == "decision":
        return b
    return None


# -------------------- citation → snippet --------------------

def _clean_snippet(lines: List[str]) -> str:
    # remove empty lines and obvious page/footer artifacts
    cleaned = [ln.strip() for ln in lines if ln and ln.strip()]
    # keep it compact
    return " ".join(cleaned).strip()


def snippet_from_citation(
    citation: Any,
    line_text_by_no: Dict[int, str],
    *,
    max_lines: int = 6,
    max_chars: int = 320,
) -> str:
    d = _cit_dump(citation)
    ls = int(d.get("line_start"))
    le = int(d.get("line_end"))
    if le < ls:
        ls, le = le, ls

    # cap number of lines for readability
    le_capped = min(le, ls + max_lines - 1)

    lines = []
    for n in range(ls, le_capped + 1):
        t = line_text_by_no.get(n)
        if t:
            lines.append(t)

    snip = _clean_snippet(lines)
    if len(snip) > max_chars:
        snip = snip[: max_chars - 1].rstrip() + "…"
    return snip


# -------------------- main renderer --------------------

def render_clinical_summary(wf: Any, *, line_text_by_no: Dict[int, str]) -> str:
    nodes = list(getattr(wf, "nodes", []) or [])
    node_map: Dict[str, Any] = {_node_id(n): n for n in nodes}

    start_id = getattr(wf, "start_node_id", None) or getattr(wf, "start", None)
    guideline_id = getattr(wf, "guideline_id", "unknown_guideline")
    wf_id = getattr(wf, "workflow_id", None) or getattr(wf, "id", None) or guideline_id
    requires_review = bool(getattr(wf, "requires_human_review", True))

    # Inputs map: in001 -> {name, description, ...}
    inputs = list(getattr(wf, "inputs", []) or [])
    input_by_id: Dict[str, dict] = {}
    for inp in inputs:
        d = _input_dump(inp)
        iid = d.get("input_id") or d.get("id")
        if iid:
            input_by_id[iid] = d

    # Walk main decision chain
    decision_chain: List[Any] = []
    seen = set()
    cur = node_map.get(start_id)

    while cur is not None and _node_kind(cur) == "decision" and _node_id(cur) not in seen:
        seen.add(_node_id(cur))
        decision_chain.append(cur)

        tnext = getattr(cur, "true_next", None)
        fnext = getattr(cur, "false_next", None)
        if not tnext or not fnext:
            break

        nxt = _pick_next_decision(node_map, tnext, fnext)
        if not nxt:
            break
        cur = node_map.get(nxt)

    actions = [n for n in nodes if _node_kind(n) == "action"]
    ends = [n for n in nodes if _node_kind(n) == "end"]

    out: List[str] = []

    # ---------------- Clinician View ----------------
    out.append(f"# Hypertension Protocol — Human Summary (`{wf_id}`)")
    out.append("")
    out.append(f"**Guideline:** `{guideline_id}`")
    out.append(f"**Human review required:** `{requires_review}`")
    out.append("")
    out.append("## How to read this")
    out.append(
        "Answer each question in order. The question text is pulled directly from the guideline whenever possible. "
        "Citations show exactly where it came from."
    )
    out.append("")

    if not decision_chain:
        out.append("*(No decision chain detected in workflow.)*")
    else:
        for idx, d in enumerate(decision_chain, start=1):
            cond = getattr(d, "condition", "")
            parsed = _parse_condition(cond)
            tnext = getattr(d, "true_next", None)
            fnext = getattr(d, "false_next", None)

            # Defaults
            gate_title = f"Step {idx}"
            question = "Does this condition apply?"
            yes_next_id, no_next_id = tnext, fnext

            if parsed:
                input_id, expected_bool = parsed
                spec = input_by_id.get(input_id, {})
                input_name = spec.get("name", input_id)
                input_desc = (spec.get("description", "") or "").strip()
                gate_title = _friendly_gate_title(input_name, idx)

                # Prefer snippet from citations; fallback to description
                cites = _citations(d)
                if cites:
                    question = snippet_from_citation(cites[0], line_text_by_no=line_text_by_no)
                elif input_desc:
                    question = input_desc
                else:
                    question = f"Is `{input_name}` true?"

                # Map YES/NO to correct branch
                if expected_bool is True:
                    yes_next_id, no_next_id = tnext, fnext
                else:
                    yes_next_id, no_next_id = fnext, tnext

            out.append(f"## {idx}. {gate_title}")
            out.append(f"**Guideline text:** {question}")
            out.append("")
            yes_node = node_map.get(yes_next_id) if yes_next_id else None
            no_node = node_map.get(no_next_id) if no_next_id else None
            out.append(f"- ✅ If **YES** → {_describe_next(yes_node) if yes_node else 'Continue.'}")
            out.append(f"- ❌ If **NO**  → {_describe_next(no_node) if no_node else 'Continue.'}")
            cites_fmt = [_fmt_citation(c) for c in _citations(d)]
            out.append("")
            out.append(f"**Evidence:** {', '.join(cites_fmt) if cites_fmt else '*(none found in this run)*'}")
            out.append("")

    # ---------------- Appendix (Engine View) ----------------
    out.append("---")
    out.append("# Appendix — Engine View (for audit/debug)")
    out.append("")
    out.append(f"- start_node_id: `{start_id}`")
    out.append("")

    out.append("## Inputs (engine IDs)")
    if inputs:
        for inp in inputs:
            d = _input_dump(inp)
            out.append(
                f"- `{d.get('input_id', d.get('id', 'in???'))}` "
                f"`{d.get('name', 'input')}` ({d.get('type', 'bool')}): "
                f"{d.get('description', '')}".rstrip()
            )
    else:
        out.append("- (No inputs found)")
    out.append("")

    out.append("## Decision chain (engine)")
    if decision_chain:
        for d in decision_chain:
            out.append(
                f"- `{_node_id(d)}`: condition=`{getattr(d, 'condition', '')}` "
                f"true_next=`{getattr(d, 'true_next', '')}` false_next=`{getattr(d, 'false_next', '')}`"
            )
    else:
        out.append("- (None)")
    out.append("")

    if actions:
        out.append("## Actions (engine)")
        for a in actions:
            cites = [_fmt_citation(c) for c in _citations(a)]
            out.append(f"- `{_node_id(a)}`: {_action_text(a)}")
            if cites:
                out.append(f"  - Evidence: {', '.join(cites)}")
        out.append("")

    if ends:
        out.append("## End states (engine)")
        for e in ends:
            out.append(f"- `{_node_id(e)}`: {_end_label(e)}")
        out.append("")

    return "\n".join(out)