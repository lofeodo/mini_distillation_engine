# pipeline/run_all.py
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence


# -------------------- helpers --------------------

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
    Supports either module.run() or module.main().
    """
    if hasattr(step_module, "run") and callable(step_module.run):
        step_module.run()
        return
    if hasattr(step_module, "main") and callable(step_module.main):
        step_module.main()
        return
    raise RuntimeError(f"{step_name}: expected a callable `run()` or `main()` in {step_module.__name__}")


def _env_snapshot(model_id: str) -> dict:
    try:
        import torch
        cuda_available = bool(torch.cuda.is_available())
        torch_version = getattr(torch, "__version__", "unknown")
        cuda_version = getattr(torch.version, "cuda", None)
    except Exception:
        cuda_available = False
        torch_version = "unavailable"
        cuda_version = None

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "model_id": model_id,
        "torch_version": torch_version,
        "cuda_available": cuda_available,
        "torch_cuda_version": cuda_version,
    }


# -------------------- paths --------------------

@dataclass(frozen=True)
class PipelinePaths:
    repo_root: Path
    data_dir: Path
    outputs_dir: Path

    guideline_txt: Path

    step1_lines: Path
    step1_chunks: Path

    step3_citation_index: Path
    step3_citation_smoketest: Path
    step3_snippets_md: Path

    step4_sanity: Path

    step5_extraction: Path
    step6_clean: Path
    step7_workflow: Path
    step8_audit_md: Path
    step9_human_md: Path

    hashes_json: Path
    run_metadata_json: Path


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
        step3_citation_index=outputs_dir / "step3_citation_index.json",
        step3_citation_smoketest=outputs_dir / "step3_citation_smoketest.json",
        step3_snippets_md=outputs_dir / "step3_citation_snippets.md",
        step4_sanity=outputs_dir / "step4_sanity.json",
        step5_extraction=outputs_dir / "step5_extraction_output.json",
        step6_clean=outputs_dir / "step6_extraction_output_clean.json",
        step7_workflow=outputs_dir / "step7_workflow.json",
        step8_audit_md=outputs_dir / "step8_workflow_audit.md",
        step9_human_md=outputs_dir / "step9_clinical_summary.md",
        hashes_json=outputs_dir / "step10_artifact_hashes.json",
        run_metadata_json=outputs_dir / "step10_run_metadata.json",
    )


def assert_prereqs(paths: PipelinePaths) -> None:
    if not paths.guideline_txt.exists():
        raise FileNotFoundError(f"Missing guideline file: {paths.guideline_txt}")


# -------------------- orchestration --------------------

def run_all(*, repo_root: Path, resume: bool, write_hashes: bool) -> None:
    paths = resolve_paths(repo_root)
    assert_prereqs(paths)

    # Keep this centralized (Step 5 currently hardcodes it too)
    model_id = "microsoft/Phi-3-mini-4k-instruct"

    # Import step runners
    from pipeline import (
        run_step1,
        run_step2,
        run_step3,
        run_step4,
        run_step5,
        run_step6,
        run_step7,
        run_step8,
        run_step9,
    )

    # NOTE:
    # - expected_outputs=None means "do not check artifacts" (used for step2 to avoid editing it right now)
    # - expected_outputs=[] is NOT used (it would break resume logic)
    steps: list[tuple[str, object, Optional[Sequence[Path]]]] = [
        ("step1", run_step1, [paths.step1_lines, paths.step1_chunks]),
        ("step2", run_step2, None),  # prints only; no artifact check
        ("step3", run_step3, [paths.step3_citation_index, paths.step3_citation_smoketest, paths.step3_snippets_md]),
        ("step4", run_step4, [paths.step4_sanity]),
        ("step5", run_step5, [paths.step5_extraction]),
        ("step6", run_step6, [paths.step6_clean]),
        ("step7", run_step7, [paths.step7_workflow]),
        ("step8", run_step8, [paths.step8_audit_md]),
        ("step9", run_step9, [paths.step9_human_md]),
    ]

    ran_steps: list[str] = []
    skipped_steps: list[str] = []

    for step_name, step_module, expected_outputs in steps:
        # resume only applies when we know what artifacts to check
        if resume and expected_outputs is not None and all(p.exists() for p in expected_outputs):
            skipped_steps.append(step_name)
            continue

        _call_step_module(step_module, step_name=step_name)

        # fail-closed artifact checks
        if expected_outputs is not None:
            missing = [str(p) for p in expected_outputs if not p.exists()]
            if missing:
                raise RuntimeError(f"{step_name} completed without producing expected artifacts: {missing}")

        ran_steps.append(step_name)

    # Integrity hashes
    hashes: dict[str, str] = {}
    if write_hashes:
        to_hash = [
            paths.guideline_txt,
            paths.step1_lines,
            paths.step1_chunks,
            paths.step3_citation_index,
            paths.step3_citation_smoketest,
            paths.step3_snippets_md,
            paths.step4_sanity,
            paths.step5_extraction,
            paths.step6_clean,
            paths.step7_workflow,
            paths.step8_audit_md,
            paths.step9_human_md,
        ]
        for p in to_hash:
            if p.exists():
                hashes[str(p.relative_to(paths.repo_root))] = sha256_file(p)
        write_json(paths.hashes_json, {"sha256": hashes})

    # Run metadata
    meta = {
        "success": True,
        "repo_root": str(paths.repo_root),
        "ran_steps": ran_steps,
        "skipped_steps": skipped_steps,
        "env": _env_snapshot(model_id=model_id),
        "artifacts": {
            "workflow_json": str(paths.step7_workflow.relative_to(paths.repo_root)) if paths.step7_workflow.exists() else None,
            "audit_md": str(paths.step8_audit_md.relative_to(paths.repo_root)) if paths.step8_audit_md.exists() else None,
            "human_md": str(paths.step9_human_md.relative_to(paths.repo_root)) if paths.step9_human_md.exists() else None,
            "hashes_json": str(paths.hashes_json.relative_to(paths.repo_root)) if (write_hashes and paths.hashes_json.exists()) else None,
        },
    }
    write_json(paths.run_metadata_json, meta)


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
        help="Disable writing outputs/step10_artifact_hashes.json",
    )

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    run_all(repo_root=repo_root, resume=args.resume, write_hashes=(not args.no_hashes))


if __name__ == "__main__":
    main()