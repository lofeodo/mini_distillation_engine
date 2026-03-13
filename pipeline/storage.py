from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from google.cloud import storage

from config import Settings


def build_gcs_uri(bucket_name: str, object_name: str) -> str:
    return f"gs://{bucket_name}/{object_name}"


class StorageBackend(ABC):
    @abstractmethod
    def upload_job_directory(self, job_id: str, local_job_dir: Path) -> dict[str, str]:
        """
        Returns a map of artifact filename -> URI/path.
        """
        raise NotImplementedError

    @abstractmethod
    def get_job_artifact_map(self, job_id: str, local_job_dir: Path) -> dict[str, str]:
        """
        Returns a map of artifact filename -> URI/path.
        """
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    def upload_job_directory(self, job_id: str, local_job_dir: Path) -> dict[str, str]:
        # Nothing to upload in local mode; just expose local file paths.
        return self.get_job_artifact_map(job_id, local_job_dir)

    def get_job_artifact_map(self, job_id: str, local_job_dir: Path) -> dict[str, str]:
        if not local_job_dir.exists():
            return {}

        artifacts: dict[str, str] = {}
        for p in sorted(local_job_dir.iterdir()):
            if p.is_file():
                artifacts[p.name] = str(p)
        return artifacts


class GCSStorageBackend(StorageBackend):
    def __init__(self, bucket_name: str) -> None:
        self.bucket_name = bucket_name
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def upload_job_directory(self, job_id: str, local_job_dir: Path) -> dict[str, str]:
        if not local_job_dir.exists():
            return {}

        artifacts: dict[str, str] = {}

        for p in sorted(local_job_dir.rglob("*")):
            if not p.is_file():
                continue

            rel_path = p.relative_to(local_job_dir).as_posix()
            object_name = f"jobs/{job_id}/{rel_path}"

            blob = self.bucket.blob(object_name)
            blob.upload_from_filename(str(p))

            artifacts[rel_path] = build_gcs_uri(self.bucket_name, object_name)

        return artifacts

    def get_job_artifact_map(self, job_id: str, local_job_dir: Path) -> dict[str, str]:
        # In GCS mode, we still compute the expected URI mapping from local files.
        if not local_job_dir.exists():
            return {}

        artifacts: dict[str, str] = {}

        for p in sorted(local_job_dir.rglob("*")):
            if not p.is_file():
                continue

            rel_path = p.relative_to(local_job_dir).as_posix()
            object_name = f"jobs/{job_id}/{rel_path}"
            artifacts[rel_path] = build_gcs_uri(self.bucket_name, object_name)

        return artifacts


def get_storage_backend(settings: Settings) -> StorageBackend:
    if settings.storage_mode == "local":
        return LocalStorageBackend()

    if settings.storage_mode == "gcs":
        if not settings.gcs_bucket:
            raise ValueError("GCS_BUCKET must be set when STORAGE_MODE='gcs'.")
        return GCSStorageBackend(settings.gcs_bucket)

    raise ValueError(f"Unsupported STORAGE_MODE: {settings.storage_mode}")