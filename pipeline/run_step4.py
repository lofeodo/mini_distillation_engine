# pipeline/run_step4.py
from __future__ import annotations

import json
from pathlib import Path

from .llm import LocalLLM, GenerationConfig, build_json_only_prompt


def _extract_first_json_object(text: str) -> dict:
    """
    Minimal, fail-closed JSON extraction for Step 4 sanity.
    Step 5 will use stronger parsing + retries.
    """
    if not text:
        raise ValueError("Model returned empty text")

    # If it's already clean JSON, great:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Otherwise, try to find first {...} region
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Could not find JSON object in output:\n{text}")

    candidate = text[start : end + 1]
    return json.loads(candidate)


def main() -> None:
    # Option A: set env var MODEL_ID before running
    #   Windows PowerShell:  $env:MODEL_ID="microsoft/Phi-3-mini-4k-instruct"
    # Option B: hardcode it here temporarily
    model_id = (Path(".") / "MODEL_ID.txt").read_text(encoding="utf-8").strip() if Path("MODEL_ID.txt").exists() else ""
    if not model_id:
        # Default fallback (change this if you want)
        model_id = "microsoft/Phi-3-mini-4k-instruct"

    llm = LocalLLM(
        model_name_or_path=model_id,
        cache_dir=None,
        seed=0,
    )

    prompt = build_json_only_prompt('{"step4_ok": true, "model_loaded": true}')
    gen = GenerationConfig(max_new_tokens=64, do_sample=False, temperature=0.0)

    out = llm.generate_text(prompt, gen=gen)
    obj = _extract_first_json_object(out)

    Path("outputs").mkdir(parents=True, exist_ok=True)
    Path("outputs/step4_sanity.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("✅ Step 4 complete.")
    print("Wrote: outputs/step4_sanity.json")
    print("Model output:", obj)


if __name__ == "__main__":
    main()