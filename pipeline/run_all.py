# pipeline/run_all.py
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Sequence


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

    guideline_txt: Path

    # canonical expected artifacts
    step1_lines: Path
    step1_chunks: Path
    step5_extraction: Path
    step6_clean: Path
    step7_workflow: Path
    step8_audit_md: Path

    # integrity + metadata
    hashes_json: Path
    run_metadata_json: Path

    # Step 3 (optional utilities) — keep consistent with run_step3.py
    step3_citation_index: Path
    step3_citation_smoketest: Path
    step3_snippets_md: Path


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
        step5_extraction=outputs_dir / "step5_extraction_output.json",
        step6_clean=outputs_dir / "step6_extraction_output_clean.json",
        step7_workflow=outputs_dir / "step7_workflow.json",
        step8_audit_md=outputs_dir / "step8_workflow_audit.md",
        hashes_json=outputs_dir / "step10_artifact_hashes.json",
        run_metadata_json=outputs_dir / "step10_run_metadata.json",
        step3_citation_index=outputs_dir / "step3_citation_index.json",
        step3_citation_smoketest=outputs_dir / "step3_citation_smoketest.json",
        step3_snippets_md=outputs_dir / "step3_citation_snippets.md",
    )


def assert_prereqs(paths: PipelinePaths) -> None:
    if not paths.guideline_txt.exists():
        raise FileNotFoundError(f"Missing guideline file: {paths.guideline_txt}")
    if not paths.repo_root.exists():
        raise FileNotFoundError(f"Repo root does not exist: {paths.repo_root}")


@dataclass(frozen=True)
class StepSpec:
    name: str
    module: object
    expected_outputs: Sequence[Path]


def _env_snapshot(model_id: str) -> dict:
    # Keep this lightweight + deterministic (no timestamps needed)
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


def run_all(*, repo_root: Path, resume: bool, write_hashes: bool) -> None:
    paths = resolve_paths(repo_root)
    assert_prereqs(paths)

    # Keep model_id centralized (Step 5 currently hardcodes it)
    # If you later move this to a config file/env var, update here too.
    model_id = "microsoft/Phi-3-mini-4k-instruct"

    # Import locally so errors are raised only when executing pipeline
    from pipeline import run_step1, run_step5, run_step6, run_step7, run_step8

    steps: list[StepSpec] = [
        StepSpec("step1", run_step1, [paths.step1_lines, paths.step1_chunks]),
        StepSpec("step5", run_step5, [paths.step5_extraction]),
        StepSpec("step6", run_step6, [paths.step6_clean]),
        StepSpec("step7", run_step7, [paths.step7_workflow]),
        StepSpec("step8", run_step8, [paths.step8_audit_md]),
    ]

    ran_steps: list[str] = []
    skipped_steps: list[str] = []

    for spec in steps:
        if resume and all(p.exists() for p in spec.expected_outputs):
            skipped_steps.append(spec.name)
            continue

        _call_step_module(spec.module, step_name=spec.name)

        missing = [str(p) for p in spec.expected_outputs if not p.exists()]
        if missing:
            raise RuntimeError(f"{spec.name} completed without producing expected artifacts: {missing}")

        ran_steps.append(spec.name)

    # Hashes (integrity layer)
    hashes: dict[str, str] = {}
    if write_hashes:
        to_hash = [
            paths.guideline_txt,
            paths.step1_lines,
            paths.step1_chunks,
            # Step3 artifacts are optional; hash them if present
            paths.step3_citation_index,
            paths.step3_citation_smoketest,
            paths.step3_snippets_md,
            paths.step5_extraction,
            paths.step6_clean,
            paths.step7_workflow,
            paths.step8_audit_md,
        ]
        for p in to_hash:
            if p.exists():
                hashes[str(p.relative_to(paths.repo_root))] = sha256_file(p)
        write_json(paths.hashes_json, {"sha256": hashes})

    # Run metadata (audit trail)
    meta = {
        "success": True,
        "repo_root": str(paths.repo_root),
        "ran_steps": ran_steps,
        "skipped_steps": skipped_steps,
        "env": _env_snapshot(model_id=model_id),
        "artifacts": {
            "guideline_txt": str(paths.guideline_txt.relative_to(paths.repo_root)),
            "step7_workflow": str(paths.step7_workflow.relative_to(paths.repo_root)),
            "step8_audit_md": str(paths.step8_audit_md.relative_to(paths.repo_root)),
            "hashes_json": str(paths.hashes_json.relative_to(paths.repo_root)) if write_hashes else None,
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