from __future__ import annotations

import json
import mimetypes
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

from app.config import get_settings


def _ensure_local_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


@lru_cache
def _storage_client():
    from google.cloud import storage
    from google.oauth2 import service_account

    settings = get_settings()
    project = settings.gcs_project_id or None

    if settings.google_application_credentials:
        path = Path(settings.google_application_credentials)
        if path.exists():
            credentials = service_account.Credentials.from_service_account_file(str(path))
            return storage.Client(project=project or credentials.project_id, credentials=credentials)

    if settings.google_credentials_json:
        info = json.loads(settings.google_credentials_json)
        credentials = service_account.Credentials.from_service_account_info(info)
        return storage.Client(project=project or credentials.project_id, credentials=credentials)

    return storage.Client(project=project)


def upload_bytes(data: bytes, object_path: str, content_type: str | None = None) -> str:
    """Upload bytes to GCS when configured, otherwise save locally.

    Returns a URL string stored on the session/document row.
    """
    settings = get_settings()
    guessed = content_type or mimetypes.guess_type(object_path)[0] or "application/octet-stream"

    if settings.use_gcs:
        client = _storage_client()
        bucket = client.bucket(settings.gcs_bucket)
        blob = bucket.blob(object_path)
        blob.upload_from_string(data, content_type=guessed)
        return f"gs://{settings.gcs_bucket}/{object_path}"

    # Local fallback for development without GCP credentials
    if object_path.startswith("audio/"):
        base = Path(settings.local_audio_dir)
    else:
        base = Path(settings.local_knowledge_dir)
    target = base / object_path.split("/", 1)[-1] if "/" in object_path else base / object_path
    # Keep nested structure under local dirs
    relative = object_path
    if object_path.startswith("audio/"):
        relative = object_path[len("audio/") :]
        base = Path(settings.local_audio_dir)
    elif object_path.startswith("knowledge/"):
        relative = object_path[len("knowledge/") :]
        base = Path(settings.local_knowledge_dir)
    target = base / relative
    _ensure_local_dir(target.parent)
    target.write_bytes(data)
    return f"file://{target.resolve()}"


def signed_or_local_url(stored_url: str | None, expires_minutes: int = 60) -> str | None:
    if not stored_url:
        return None

    if stored_url.startswith("file://"):
        # Served via API proxy endpoint instead
        return None

    if stored_url.startswith("gs://"):
        settings = get_settings()
        # gs://bucket/path
        without = stored_url[5:]
        bucket_name, _, blob_name = without.partition("/")
        if not blob_name:
            return None
        client = _storage_client()
        bucket = client.bucket(bucket_name or settings.gcs_bucket)
        blob = bucket.blob(blob_name)
        return blob.generate_signed_url(
            expiration=timedelta(minutes=expires_minutes),
            method="GET",
            version="v4",
        )

    return stored_url


def read_bytes(stored_url: str) -> bytes:
    if stored_url.startswith("file://"):
        path = Path(stored_url.removeprefix("file://"))
        return path.read_bytes()

    if stored_url.startswith("gs://"):
        without = stored_url[5:]
        bucket_name, _, blob_name = without.partition("/")
        client = _storage_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.download_as_bytes()

    raise ValueError(f"Unsupported storage URL: {stored_url}")

