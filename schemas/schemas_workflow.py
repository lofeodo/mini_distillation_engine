# pipeline/schemas_workflow.py
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field, ConfigDict


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    line_start: int
    line_end: int
    quote: Optional[str] = None


class InputSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_id: str = Field(..., pattern=r"^in\d{3}$", description="e.g., in001")
    name: str
    type: Literal["bool", "int", "float", "str", "choice"]
    description: Optional[str] = None
    choices: Optional[List[str]] = None  # only for type == "choice"


class NodeType(str, Enum):
    DECISION = "decision"
    ACTION = "action"
    END = "end"


class DecisionNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(..., pattern=r"^d\d{4}$")
    node_type: Literal["decision"] = "decision"

    # Keep this intentionally simple and auditable:
    # a boolean expression over inputs (and optionally named constants).
    condition: str = Field(..., min_length=1, description="e.g., 'in001 == true and in002 >= 140'")
    true_next: str = Field(..., description="node_id to follow if condition true")
    false_next: str = Field(..., description="node_id to follow if condition false")

    citations: List[Citation] = Field(default_factory=list)


class ActionNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(..., pattern=r"^a\d{4}$")
    node_type: Literal["action"] = "action"

    action: str = Field(..., min_length=1)
    requires_human_review: bool = False
    citations: List[Citation] = Field(default_factory=list)


class EndNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(..., pattern=r"^e\d{4}$")
    node_type: Literal["end"] = "end"
    label: Optional[str] = None


WorkflowNode = DecisionNode | ActionNode | EndNode


class Workflow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str = Field(..., min_length=1)
    guideline_id: str = Field(..., min_length=1)

    inputs: List[InputSpec] = Field(default_factory=list)

    # A flat node list keeps it portable; graph validated deterministically.
    nodes: List[WorkflowNode] = Field(..., min_length=1)

    start_node_id: str

    requires_human_review: bool = False
    warnings: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)