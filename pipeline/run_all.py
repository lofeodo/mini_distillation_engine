# pipeline/run_all.py
from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


# --- small helpers ------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _call_step_module(step_module, *, step_name: str) -> None:
    """
    Supports either:
      - module.run()
      - module.main()
    If neither exists, raises (fail-closed).
    """
    fn: Optional[Callable[[], None]] = None
    if hasattr(step_module, "run") and callable(step_module.run):
        fn = step_module.run
    elif hasattr(step_module, "main") and callable(step_module.main):
        fn = step_module.main

    if fn is None:
        raise RuntimeError(
            f"{step_name}: expected a callable `run()` or `main()` in {step_module.__name__}"
        )

    fn()


@dataclass(frozen=True)
class PipelinePaths:
    repo_root: Path
    data_dir: Path
    outputs_dir: Path

    # canonical expected artifacts (based on your repo structure)
    guideline_txt: Path
    step1_lines: Path
    step1_chunks: Path
    step3_trace_index: Path
    step5_extraction: Path
    step6_clean: Path
    step7_workflow: Path
    step8_audit_md: Path
    step8_hashes: Path


def resolve_paths(repo_root: Path) -> PipelinePaths:
    data_dir = repo_root / "data"
    outputs_dir = repo_root / "outputs"

    return PipelinePaths(
        repo_root=repo_root,
        data_dir=data_dir,
        outputs_dir=outputs_dir,
        guideline_txt=data_dir / "guideline.txt",
        step1_lines=outputs_dir / "step1_lines.json",
        step1_chunks=outputs_dir / "step1_chunks.json",
        step3_trace_index=outputs_dir / "step3_trace_index.json",
        step5_extraction=outputs_dir / "step5_extraction_output.json",
        step6_clean=outputs_dir / "step6_extraction_output_clean.json",
        step7_workflow=outputs_dir / "step7_workflow.json",
        step8_audit_md=outputs_dir / "step8_workflow_audit.md",
        step8_hashes=outputs_dir / "step8_artifact_hashes.json",
    )


def assert_prereqs(paths: PipelinePaths) -> None:
    if not paths.guideline_txt.exists():
        raise FileNotFoundError(f"Missing guideline file: {paths.guideline_txt}")

    # outputs dir is created as needed, but repo_root must be sane
    if not paths.repo_root.exists():
        raise FileNotFoundError(f"Repo root does not exist: {paths.repo_root}")


def run_all(*, repo_root: Path, resume: bool, write_hashes: bool) -> None:
    paths = resolve_paths(repo_root)
    assert_prereqs(paths)

    # Import locally so errors are raised only when executing pipeline
    from pipeline import (
        run_step1,
        run_step5,
        run_step6,
        run_step7,
        run_step8,
    )

    # Step execution plan with “done” checks for resume mode
    steps = [
        ("step1", run_step1, [paths.step1_lines, paths.step1_chunks]),
        ("step5", run_step5, [paths.step5_extraction]),
        ("step6", run_step6, [paths.step6_clean]),
        ("step7", run_step7, [paths.step7_workflow]),
        ("step8", run_step8, [paths.step8_audit_md]),
    ]

    for step_name, step_module, expected_outputs in steps:
        if resume and all(p.exists() for p in expected_outputs):
            # Deterministic skip (no partial reruns)
            continue

        _call_step_module(step_module, step_name=step_name)

        # Fail-closed: if the step says it succeeded, its artifacts MUST exist
        missing = [str(p) for p in expected_outputs if not p.exists()]
        if missing:
            raise RuntimeError(
                f"{step_name} completed without producing expected artifacts: {missing}"
            )

    if write_hashes:
        hashes: dict[str, str] = {}
        # Hash the “high-value” artifacts for reproducibility / audit trails
        to_hash = [
            paths.guideline_txt,
            paths.step1_lines,
            paths.step1_chunks,
            paths.step3_trace_index,   # might be created earlier by step3 utility runner, still useful if present
            paths.step5_extraction,
            paths.step6_clean,
            paths.step7_workflow,
            paths.step8_audit_md,
        ]
        for p in to_hash:
            if p.exists():
                hashes[str(p.relative_to(paths.repo_root))] = sha256_file(p)

        write_json(paths.step8_hashes, {"sha256": hashes})


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full guideline distillation pipeline (fail-closed).")
    parser.add_argument(
        "--repo-root",
        type=str,
        default=str(Path(__file__).resolve().parents[1]),
        help="Path to the repository root (defaults to project root).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip steps whose expected output artifacts already exist.",
    )
    parser.add_argument(
        "--no-hashes",
        action="store_true",
        help="Disable writing outputs/step8_artifact_hashes.json",
    )

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    run_all(repo_root=repo_root, resume=args.resume, write_hashes=(not args.no_hashes))


if __name__ == "__main__":
    main()