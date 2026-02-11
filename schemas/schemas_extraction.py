# pipeline/schemas_extraction.py
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field, ConfigDict


class Strength(str, Enum):
    MUST = "must"
    SHOULD = "should"
    MAY = "may"
    CONSIDER = "consider"
    UNCLEAR = "unclear"


class FactType(str, Enum):
    POPULATION = "population"
    THRESHOLD = "threshold"
    EXCLUSION = "exclusion"
    CONTRAINDICATION = "contraindication"
    RED_FLAG = "red_flag"
    ACTION = "action"
    DIAGNOSTIC = "diagnostic"
    FOLLOW_UP = "follow_up"
    OTHER = "other"


class Citation(BaseModel):
    """
    Mirrors pipeline/contracts.py Citation structure, but kept local here
    so extraction schemas remain self-contained.
    """
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    line_start: int
    line_end: int
    quote: Optional[str] = None


class ExtractedFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_id: str = Field(..., pattern=r"^f\d{4}$", description="Stable ID like f0001")
    fact_type: FactType

    # Human-readable normalized statement of what the guideline says (no invention)
    statement: str = Field(..., min_length=1)

    # Strength of recommendation / language signal
    strength: Strength = Strength.UNCLEAR

    # If language is ambiguous (“consider”, “may”), this must be true.
    requires_human_review: bool = False

    # Optional structured hooks (kept intentionally light; don’t over-engineer yet)
    subject: Optional[str] = Field(default=None, description="e.g., 'adult patients with HTN'")
    condition: Optional[str] = Field(default=None, description="e.g., 'SBP >= 140'")
    action: Optional[str] = Field(default=None, description="e.g., 'start antihypertensive therapy'")
    notes: Optional[str] = None

    citations: List[Citation] = Field(..., min_length=1)

    # For traceability/debug: allow model to include raw snippet refs without breaking determinism
    raw: Optional[Dict[str, Any]] = None


class ExtractionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    guideline_id: str = Field(..., min_length=1)
    model_id: str = Field(..., min_length=1)

    # chunking params are part of auditability
    chunking: Dict[str, Any] = Field(default_factory=dict)

    extracted_facts: List[ExtractedFact] = Field(default_factory=list)

    # global warnings (e.g., “PDF had weird whitespace”, “LLM returned malformed JSON then recovered”)
    warnings: List[str] = Field(default_factory=list)

    # metadata for reproducibility
    meta: Dict[str, Any] = Field(default_factory=dict)