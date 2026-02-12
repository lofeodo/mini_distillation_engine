# pipeline/extract.py
from __future__ import annotations

import json
from typing import List, Dict, Any

from tenacity import retry, stop_after_attempt, wait_fixed

from .llm import LocalLLM, GenerationConfig, build_json_only_prompt
from .traceability import build_trace_index, validate_citations_list
from .io_utils import read_json, write_json
from pydantic import BaseModel, ConfigDict, Field
from schemas.schemas_extraction import ExtractionOutput, ExtractedFact  # adjust path if needed


class ChunkExtractionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    extracted_facts: list[ExtractedFact] = Field(default_factory=list)


class ExtractionError(Exception):
    pass


def normalize_fact_types(obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically normalize common near-miss fact_type values
    into the strict FactType enum values.
    Fail-closed for truly unknown values.
    """
    mapping = {
        "precaution": "other",          # or "red_flag" if you prefer
        "precautions": "other",
        "warning": "red_flag",
        "warnings": "red_flag",
        "contraindications": "contraindication",
        "contraindication": "contraindication",
        "diagnosis": "diagnostic",
        "followup": "follow_up",
        "follow-up": "follow_up",
    }

    facts = obj.get("extracted_facts")
    if not isinstance(facts, list):
        return obj

    for f in facts:
        if not isinstance(f, dict):
            continue
        ft = f.get("fact_type")
        if isinstance(ft, str):
            key = ft.strip().lower()
            if key in mapping:
                f["fact_type"] = mapping[key]

    return obj


def normalize_citations_to_chunk(obj: Dict[str, Any], chunk: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically constrain model-provided citations to the current chunk bounds.
    - Forces chunk_id to current chunk_id (since extraction is per-chunk).
    - Clamps line_start/line_end into [chunk.line_start, chunk.line_end].
    - Drops citations that are completely out of range (fail-closed at fact-level).
    """
    facts = obj.get("extracted_facts")
    if not isinstance(facts, list):
        return obj

    cid = chunk["chunk_id"]
    ls = int(chunk["line_start"])
    le = int(chunk["line_end"])

    for f in facts:
        if not isinstance(f, dict):
            continue
        cits = f.get("citations")
        if not isinstance(cits, list):
            continue

        new_cits = []
        for c in cits:
            if not isinstance(c, dict):
                continue

            # force chunk_id
            c["chunk_id"] = cid

            # clamp lines if present
            try:
                c_ls = int(c.get("line_start", ls))
                c_le = int(c.get("line_end", le))
            except Exception:
                continue

            # if totally outside, drop
            if c_le < ls or c_ls > le:
                continue

            c_ls = max(ls, min(le, c_ls))
            c_le = max(ls, min(le, c_le))
            if c_ls > c_le:
                c_ls, c_le = c_le, c_ls

            c["line_start"] = c_ls
            c["line_end"] = c_le
            new_cits.append(c)

        f["citations"] = new_cits

    return obj


def build_extraction_prompt(chunk: Dict[str, Any]) -> str:
    """
    Prompt the LLM to return ONLY per-chunk extracted facts:
      {"extracted_facts":[...]}
    Keep output short to avoid truncation (tables can explode).
    """
    schema_hint = {
        "extracted_facts": [
            {
                "fact_id": "f0001",
                "fact_type": "other",
                "statement": "<statement copied from TEXT>",
                "strength": "unclear",
                "requires_human_review": False,
                "citations": [
                    {"chunk_id": chunk["chunk_id"], "line_start": chunk["line_start"], "line_end": chunk["line_end"]}
                ],
            }
        ]
    }

def build_extraction_prompt(chunk: Dict[str, Any]) -> str:
    """
    Strict per-chunk extraction prompt.
    Returns ONLY:
        {"extracted_facts":[...]}
    """

    schema_hint = {
        "extracted_facts": [
            {
                "fact_id": "f0001",
                "fact_type": "other",
                "statement": "<statement copied from TEXT>",
                "strength": "unclear",
                "requires_human_review": False,
                "citations": [
                    {
                        "chunk_id": chunk["chunk_id"],
                        "line_start": chunk["line_start"],
                        "line_end": chunk["line_end"],
                    }
                ],
            }
        ]
    }

    return (
        "You are a strict JSON-only clinical extraction engine.\n"
        "Return ONLY a single valid JSON object.\n"
        "No prose. No markdown. No explanations.\n"
        "The first character must be '{' and the last must be '}'.\n\n"
        "Task:\n"
        "- Extract ONLY explicitly stated clinical facts from the TEXT.\n"
        "- The statement MUST be copied verbatim (or near-verbatim) from the TEXT.\n"
        "- Do NOT reuse the example wording.\n"
        "- Do NOT infer or generalize.\n"
        "- If no extractable clinical facts are present, return: {\"extracted_facts\": []}\n"
        "- If the TEXT is a table or repeated bullet list, extract at most 1–3 high-level facts.\n"
        "- Hard limit: output at most 3 facts.\n"
        "- Every fact MUST include at least one citation within this chunk bounds.\n"
        "- Output statements in the SAME LANGUAGE as the TEXT.\n\n"
        "Allowed enums:\n"
        "- fact_type: population, threshold, exclusion, contraindication, red_flag, action, diagnostic, follow_up, other\n"
        "- strength: must, should, may, consider, unclear\n\n"
        f"Chunk metadata:\n"
        f"- chunk_id: {chunk['chunk_id']}\n"
        f"- line_start: {chunk['line_start']}\n"
        f"- line_end: {chunk['line_end']}\n\n"
        "Required JSON shape example (values are placeholders; do NOT copy them):\n"
        f"{json.dumps(schema_hint, ensure_ascii=False)}\n\n"
        "TEXT:\n"
        f"{chunk['text']}\n\n"
        "Output JSON below:\n"
    )


def recover_truncated_chunk_json(text: str) -> str | None:
    """
    Recover truncated JSON of the form:
      {"extracted_facts":[ {...}, {...}, ... ]}
    by keeping only fully-closed fact objects and closing the array/object.

    We detect the last position where a FACT object is closed:
      - root object depth == 1
      - extracted_facts array depth == 1
      - just closed a fact object (object depth returns to 1 while still inside the array)
    """
    s = (text or "").strip()
    if not s.startswith('{"extracted_facts"'):
        return None

    in_str = False
    esc = False
    obj_depth = 0
    arr_depth = 0
    last_safe_end = None

    for i, ch in enumerate(s):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
            continue

        if ch == "{":
            obj_depth += 1
        elif ch == "}":
            obj_depth = max(0, obj_depth - 1)
            # If we've just closed a fact object, we're back to root depth (1) while inside array (1)
            if obj_depth == 1 and arr_depth == 1:
                last_safe_end = i
        elif ch == "[":
            arr_depth += 1
        elif ch == "]":
            arr_depth = max(0, arr_depth - 1)

    if last_safe_end is None:
        return None

    cut = s[: last_safe_end + 1].rstrip()
    # remove trailing comma if somehow present
    if cut.endswith(","):
        cut = cut[:-1].rstrip()

    return cut + "]}"


def parse_json_strict(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ExtractionError("Empty model output")

    # 1) direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2) try first {...} span
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1].strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # 3) deterministic recovery for truncated chunk JSON
    recovered = recover_truncated_chunk_json(text)
    if recovered is not None:
        try:
            obj = json.loads(recovered)
            # mark it so you can surface it later as an audit warning
            obj.setdefault("_recovered", True)
            return obj
        except json.JSONDecodeError:
            pass

    raise ExtractionError(f"Invalid JSON output (unrecoverable). Output was:\n{text}")


def validate_extraction_output(
    obj: Dict[str, Any],
    trace_index: Dict[str, Any],
) -> ExtractionOutput:
    parsed = ExtractionOutput.model_validate(obj)

    for fact in parsed.extracted_facts:
        # validate_citations_list expects list[dict]
        validate_citations_list(trace_index, [c.model_dump() for c in fact.citations])

    return parsed


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def extract_chunk(
    llm: LocalLLM,
    chunk: Dict[str, Any],
    trace_index: Dict[str, Any],
) -> ChunkExtractionOutput:
    """
    Generate per-chunk JSON: {"extracted_facts":[...]} with bounded incremental decoding.

    Robustness:
    - Forces JSON start ("{") to prevent document-continuation behavior.
    - Parses/retries until JSON is valid (or token cap hit).
    - Deterministically normalizes:
        * fact_type near-misses (e.g., precaution -> other)
        * citations to current chunk bounds (forces chunk_id + clamps line ranges)
    - Fail-closed if any fact ends up with zero valid citations.
    """

    prompt = build_extraction_prompt(chunk)

    # Force JSON start to avoid "continue the document" behavior
    base_prompt = prompt + "{"
    accumulated = "{"

    hard_cap_tokens = 1800
    step_tokens = 256
    generated = 0

    while generated < hard_cap_tokens:
        raw = llm.generate_text(
            base_prompt + accumulated[1:],  # continue after the initial "{"
            GenerationConfig(max_new_tokens=step_tokens),
        )
        accumulated += raw
        generated += step_tokens

        try:
            obj = parse_json_strict(accumulated)
            obj.pop("_recovered", None)

            # Deterministic cleanup BEFORE schema validation
            obj = normalize_citations_to_chunk(obj, chunk)
            obj = normalize_fact_types(obj)

            parsed = ChunkExtractionOutput.model_validate(obj)

            # Citation bounds enforcement (Step 3) + fail-closed if citations vanished
            for fact in parsed.extracted_facts:
                if not fact.citations:
                    raise ExtractionError("Fact has zero valid citations after normalization.")
                validate_citations_list(trace_index, [c.model_dump() for c in fact.citations])

            return parsed

        except ExtractionError:
            # Not parseable yet (or citations invalid); continue generating
            continue
        except Exception as e:
            # Schema errors should fail this attempt and trigger tenacity retry
            raise ExtractionError(f"Schema validation failed: {e}\nOutput was:\n{accumulated}") from e

    # One last attempt (including truncation recovery) before failing
    try:
        obj = parse_json_strict(accumulated)
        obj.pop("_recovered", None)
        obj = normalize_citations_to_chunk(obj, chunk)
        obj = normalize_fact_types(obj)
        parsed = ChunkExtractionOutput.model_validate(obj)
        for fact in parsed.extracted_facts:
            if not fact.citations:
                raise ExtractionError("Fact has zero valid citations after normalization.")
            validate_citations_list(trace_index, [c.model_dump() for c in fact.citations])
        return parsed
    except Exception:
        pass

    raise ExtractionError(
        f"Model did not produce valid JSON within token cap. Partial output:\n{accumulated[:2000]}"
    )


def run_extraction(
    model_id: str,
    guideline_id: str = "inesss_hypertension",
    chunks_path: str = "outputs/step1_chunks.json",
) -> Dict[str, Any]:

    trace_index = build_trace_index()
    chunks = read_json(chunks_path)
    llm = LocalLLM(model_id, seed=0)

    chunking = {
        "hard_limit_lines": 20,
        "soft_limit_chars": 1200,
        "num_chunks": len(chunks),
    }

    all_facts: list[ExtractedFact] = []
    warnings: list[str] = []

    for chunk in chunks:
        per_chunk = extract_chunk(llm, chunk, trace_index)
        all_facts.extend(per_chunk.extracted_facts)

    # Deterministically re-assign global unique fact_ids (f0001..fNNNN)
    for i, fact in enumerate(all_facts, start=1):
        fact.fact_id = f"f{i:04d}"

    out = ExtractionOutput(
        guideline_id=guideline_id,
        model_id=model_id,
        chunking=chunking,
        extracted_facts=all_facts,
        warnings=warnings,
        meta={},
    )

    return out.model_dump()