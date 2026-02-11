# pipeline/validate_workflow.py
from __future__ import annotations

from typing import Dict, List, Any, Set

from pipeline.schemas_workflow import Workflow, DecisionNode, ActionNode, EndNode


class WorkflowValidationError(ValueError):
    pass


def validate_workflow_graph(workflow: Workflow) -> None:
    nodes = workflow.nodes
    node_ids = [n.node_id for n in nodes]
    if len(node_ids) != len(set(node_ids)):
        raise WorkflowValidationError("Duplicate node_id detected in workflow.nodes")

    node_map: Dict[str, Any] = {n.node_id: n for n in nodes}

    if workflow.start_node_id not in node_map:
        raise WorkflowValidationError(f"start_node_id not found: {workflow.start_node_id}")

    # Validate edges
    for n in nodes:
        if isinstance(n, DecisionNode):
            if n.true_next not in node_map:
                raise WorkflowValidationError(f"{n.node_id}.true_next missing: {n.true_next}")
            if n.false_next not in node_map:
                raise WorkflowValidationError(f"{n.node_id}.false_next missing: {n.false_next}")

    # Optional: reachability (fail closed if dead/unreachable nodes)
    reachable: Set[str] = set()
    stack = [workflow.start_node_id]
    while stack:
        cur = stack.pop()
        if cur in reachable:
            continue
        reachable.add(cur)
        node = node_map[cur]
        if isinstance(node, DecisionNode):
            stack.append(node.true_next)
            stack.append(node.false_next)

    unreachable = set(node_map.keys()) - reachable
    if unreachable:
        raise WorkflowValidationError(f"Unreachable nodes detected: {sorted(unreachable)}")