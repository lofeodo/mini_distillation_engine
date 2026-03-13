from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from config import get_settings


settings = get_settings()

app = FastAPI(title="Guideline Distillation Service")


# ---------------------------
# Request models
# ---------------------------

class CreateJobRequest(BaseModel):
    guideline_text: str = Field(..., min_length=1)
    guideline_id: str | None = None
    model_id: str | None = None


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
def create_job(req: CreateJobRequest):

    job_id = str(uuid.uuid4())
    d = job_dir(job_id)

    guideline_path = d / "guideline.txt"
    guideline_path.write_text(req.guideline_text, encoding="utf-8")

    status = {
        "job_id": job_id,
        "status": "running",
        "created_at": utc_now(),
        "completed_at": None,
        "input_path": str(guideline_path),
        "local_output_dir": str(d),
        "error_message": None
    }

    write_json(job_status_path(job_id), status)

    # NOTE: pipeline call will be added in the next step

    status["status"] = "completed"
    status["completed_at"] = utc_now()

    write_json(job_status_path(job_id), status)

    return {
        "job_id": job_id,
        "status": status["status"],
        "job_dir": str(d)
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