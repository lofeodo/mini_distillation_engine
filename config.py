from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """
    Centralized application configuration.

    Values are loaded from environment variables so the same code can run:
    - locally
    - inside Docker
    - on Cloud Run
    """

    # environment
    app_env: str = os.getenv("APP_ENV", "dev")

    # model configuration
    model_id: str = os.getenv("MODEL_ID", "microsoft/Phi-3-mini-4k-instruct")

    # default guideline
    guideline_id: str = "inesss_hypertension"

    # storage mode: "local" or "gcs"
    storage_mode: str = os.getenv("STORAGE_MODE", "local").strip().lower()

    # where job directories will live locally
    local_jobs_dir: Path = Path(os.getenv("LOCAL_JOBS_DIR", "jobs"))

    # server port (Cloud Run injects this automatically)
    port: int = int(os.getenv("PORT", "8080"))

    # optional huggingface cache override
    hf_home: str | None = os.getenv("HF_HOME")

    # GCP / GCS settings
    gcp_project: str | None = os.getenv("GCP_PROJECT")
    gcp_region: str = os.getenv("GCP_REGION", "northamerica-northeast1")
    gcs_bucket: str | None = os.getenv("GCS_BUCKET")


def get_settings() -> Settings:
    settings = Settings()

    if settings.storage_mode not in {"local", "gcs"}:
        raise ValueError("STORAGE_MODE must be either 'local' or 'gcs'.")

    if settings.storage_mode == "gcs" and not settings.gcs_bucket:
        raise ValueError("GCS_BUCKET must be set when STORAGE_MODE='gcs'.")

    return settings