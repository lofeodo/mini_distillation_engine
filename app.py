from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from pipeline.run_all import run_all_for_job
from pipeline.source_to_guideline import build_guideline_txt_from_pdf

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from config import get_settings


settings = get_settings()

app = FastAPI(title="Guideline Distillation Service")

# ---------------------------
# Utility functions
# ---------------------------

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def job_dir(job_id: str) -> Path:
    d = settings.local_jobs_dir / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def job_status_path(job_id: str) -> Path:
    return job_dir(job_id) / "job_status.json"


# ---------------------------
# Endpoints
# ---------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/jobs")
async def create_job(
    file: UploadFile = File(...),
    model_id: str | None = Form(None),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="missing filename")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="only PDF files are supported")

    job_id = str(uuid.uuid4())
    d = job_dir(job_id)

    # Save the uploaded PDF to a canonical internal name
    pdf_path = d / "guideline.pdf"
    pdf_bytes = await file.read()
    pdf_path.write_bytes(pdf_bytes)

    # Convert PDF -> canonical guideline.txt using existing pipeline utility
    guideline_path = d / "guideline.txt"
    build_guideline_txt_from_pdf(pdf_path, guideline_path)

    status = {
        "job_id": job_id,
        "status": "running",
        "created_at": utc_now(),
        "completed_at": None,
        "input_path": str(pdf_path),
        "original_filename": file.filename,
        "normalized_input_path": str(guideline_path),
        "local_output_dir": str(d),
        "error_message": None,
    }

    write_json(job_status_path(job_id), status)

    try:
        run_all_for_job(
            guideline_path=guideline_path,
            output_dir=d,
            model_id=model_id or settings.model_id,
        )
    except Exception as e:
        status["status"] = "failed"
        status["completed_at"] = utc_now()
        status["error_message"] = str(e)
        write_json(job_status_path(job_id), status)
        raise HTTPException(status_code=500, detail=f"job failed: {e}")

    status["status"] = "completed"
    status["completed_at"] = utc_now()
    write_json(job_status_path(job_id), status)

    return {
        "job_id": job_id,
        "status": status["status"],
        "job_dir": str(d),
    }


@app.get("/jobs/{job_id}")
def get_job(job_id: str):

    path = job_status_path(job_id)

    if not path.exists():
        raise HTTPException(404, "job not found")

    return read_json(path)


@app.get("/jobs/{job_id}/artifacts")
def get_artifacts(job_id: str):

    d = settings.local_jobs_dir / job_id

    if not d.exists():
        raise HTTPException(404, "job not found")

    artifacts = {}

    for p in d.iterdir():
        artifacts[p.name] = str(p)

    return {
        "job_id": job_id,
        "artifacts": artifacts
    }