# pipeline/synthesize_workflow.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Set, Tuple

from schemas.schemas_extraction import ExtractionOutput, ExtractedFact, FactType
from schemas.schemas_workflow import (
    Workflow,
    InputSpec,
    DecisionNode,
    ActionNode,
    EndNode,
    Citation as WFCitation,
)


@dataclass
class IdGen:
    d: int = 0
    a: int = 0
    e: int = 0

    def d_id(self) -> str:
        self.d += 1
        return f"d{self.d:04d}"

    def a_id(self) -> str:
        self.a += 1
        return f"a{self.a:04d}"

    def e_id(self) -> str:
        self.e += 1
        return f"e{self.e:04d}"


def _cap_citations(cits: List[WFCitation], max_n: int) -> List[WFCitation]:
    # deterministic: keep first N in existing stable order
    if max_n <= 0:
        return []
    return cits[:max_n]


def _merge_citations(facts: Iterable[ExtractedFact]) -> List[WFCitation]:
    seen: Set[Tuple[str, int, int]] = set()
    out: List[WFCitation] = []

    all_cits = []
    for f in facts:
        all_cits.extend(f.citations)

    all_cits.sort(key=lambda c: (c.chunk_id, c.line_start, c.line_end))
    for c in all_cits:
        key = (c.chunk_id, c.line_start, c.line_end)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            WFCitation(
                chunk_id=c.chunk_id,
                line_start=c.line_start,
                line_end=c.line_end,
                quote=c.quote,
            )
        )
    return out


def synthesize_workflow(ex: ExtractionOutput) -> Workflow:
    ids = IdGen()

    # Buckets
    population = [f for f in ex.extracted_facts if f.fact_type == FactType.POPULATION]
    excl_contra = [
        f
        for f in ex.extracted_facts
        if f.fact_type in {FactType.EXCLUSION, FactType.CONTRAINDICATION}
    ]
    red_flags = [f for f in ex.extracted_facts if f.fact_type == FactType.RED_FLAG]
    review_facts = [f for f in ex.extracted_facts if f.requires_human_review]

    # Inputs (minimal executable “funnel”)
    inputs = [
        InputSpec(
            input_id="in001",
            name="meets_population",
            type="bool",
            description="True if the patient matches the guideline population definition.",
        ),
        InputSpec(
            input_id="in002",
            name="has_exclusion_or_contraindication",
            type="bool",
            description="True if any guideline exclusion or contraindication applies.",
        ),
        InputSpec(
            input_id="in003",
            name="has_red_flags",
            type="bool",
            description="True if any guideline red flag is present.",
        ),
    ]

    # ---------------------------------------------------------------------
    # IMPORTANT: DecisionNode.true_next / false_next must be strings (no None).
    # So we pre-allocate IDs for every node first.
    # ---------------------------------------------------------------------
    e_not_applicable_id = ids.e_id()
    e_excluded_id = ids.e_id()

    a_red_flags_id = ids.a_id()
    a_review_id = ids.a_id()

    d_population_id = ids.d_id()
    d_excl_id = ids.d_id()
    d_red_id = ids.d_id()

    # End nodes
    e_not_applicable = EndNode(
        node_id=e_not_applicable_id,
        label="Not applicable (outside population)",
    )
    e_excluded = EndNode(
        node_id=e_excluded_id,
        label="Excluded / contraindicated",
    )

    # Action nodes (conservative wording: structured summary, not autonomy)
    a_red_flags = ActionNode(
        node_id=a_red_flags_id,
        action=(
            "Guideline red flags present: escalate to urgent evaluation / clinician-directed "
            "management per guideline context."
        ),
        requires_human_review=True,
        citations=_merge_citations(red_flags),
    )

    # Build review citations (can be very broad). Keep deterministic cap for readability.
    review_cits_full = _merge_citations(review_facts if review_facts else ex.extracted_facts)
    review_cits = _cap_citations(review_cits_full, max_n=8)

    a_review = ActionNode(
        node_id=a_review_id,
        action=(
            "No exclusions/contraindications and no red flags detected. Review the extracted guideline "
            "facts and apply clinically. This workflow is a structured summary, not autonomous medical decision-making."
        ),
        requires_human_review=True,
        citations=review_cits,
    )

    # Decision nodes (now fully wired with string next pointers)
    d_population = DecisionNode(
        node_id=d_population_id,
        condition="in001 == true",
        true_next=d_excl_id,
        false_next=e_not_applicable_id,
        citations=_merge_citations(population),
    )

    d_excl = DecisionNode(
        node_id=d_excl_id,
        condition="in002 == true",
        true_next=e_excluded_id,
        false_next=d_red_id,
        citations=_merge_citations(excl_contra),
    )

    d_red = DecisionNode(
        node_id=d_red_id,
        condition="in003 == true",
        true_next=a_red_flags_id,
        false_next=a_review_id,
        citations=_merge_citations(red_flags),
    )

    warnings: List[str] = []
    if not population:
        warnings.append(
            "Step7: no POPULATION facts found; population gate may require manual interpretation."
        )
    if not excl_contra:
        warnings.append(
            "Step7: no EXCLUSION/CONTRAINDICATION facts found; exclusion gate may be incomplete."
        )
    if not red_flags:
        warnings.append(
            "Step7: no RED_FLAG facts found; the red-flag decision node is a template gate with no "
            "fact-derived criteria in this run."
        )

    nodes = [
        d_population,
        d_excl,
        d_red,
        a_red_flags,
        a_review,
        e_not_applicable,
        e_excluded,
    ]

    return Workflow(
        workflow_id=f"{ex.guideline_id}__v1",
        guideline_id=ex.guideline_id,
        inputs=inputs,
        nodes=nodes,
        start_node_id=d_population_id,
        requires_human_review=True,
        warnings=warnings,
        meta={
            "source": {
                "step": 7,
                "input_artifact": "outputs/step6_extraction_output_clean.json",
                "num_facts": len(ex.extracted_facts),
                "num_population_facts": len(population),
                "num_excl_contra_facts": len(excl_contra),
                "num_red_flag_facts": len(red_flags),
                "num_review_facts": len(review_facts),
                "review_citations_available": len(review_cits_full),
                "review_citations_emitted": len(review_cits),
            }
        },
    )