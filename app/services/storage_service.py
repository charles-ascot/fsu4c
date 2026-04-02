from __future__ import annotations

import json
import logging
from datetime import datetime

from google.cloud import storage

from app.core.config import GCS_BUCKET

logger = logging.getLogger(__name__)

_client: storage.Client | None = None


def _get_client() -> storage.Client:
    global _client
    if _client is None:
        _client = storage.Client()
    return _client


def _bucket() -> storage.Bucket:
    return _get_client().bucket(GCS_BUCKET)


# ── GCS path helpers ──────────────────────────────────────────────────────────

def raw_prefix(space_resource_name: str, message_id: str, received_at: datetime) -> str:
    """raw/{year}/{month}/{day}/{space_id}/{message_id}/"""
    space_slug = space_resource_name.replace("/", "_")
    return (
        f"raw/{received_at.year:04d}/{received_at.month:02d}/"
        f"{received_at.day:02d}/{space_slug}/{message_id.replace('/', '_')}/"
    )


def processed_prefix(record_id: str) -> str:
    """processed/{record_id}/"""
    return f"processed/{record_id}/"


def daily_manifest_path(date: datetime) -> str:
    return f"index/daily_manifest_{date.strftime('%Y-%m-%d')}.json"


# ── Upload helpers ────────────────────────────────────────────────────────────

def upload_bytes(gcs_path: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    blob = _bucket().blob(gcs_path)
    blob.upload_from_string(data, content_type=content_type)
    logger.debug("Uploaded %d bytes to gs://%s/%s", len(data), GCS_BUCKET, gcs_path)
    return gcs_path


def upload_text(gcs_path: str, text: str, content_type: str = "text/plain; charset=utf-8") -> str:
    return upload_bytes(gcs_path, text.encode("utf-8"), content_type)


def upload_json(gcs_path: str, obj: dict) -> str:
    data = json.dumps(obj, indent=2, default=str).encode("utf-8")
    return upload_bytes(gcs_path, data, "application/json")


def download_json(gcs_path: str) -> dict:
    blob = _bucket().blob(gcs_path)
    return json.loads(blob.download_as_bytes())


def blob_exists(gcs_path: str) -> bool:
    return _bucket().blob(gcs_path).exists()


# ── Chat-specific store operations ────────────────────────────────────────────

def store_raw_message(
    message_id: str,
    space_resource_name: str,
    received_at: datetime,
    raw_message: dict,
) -> str:
    """
    Store raw Chat message JSON under:
      raw/{year}/{month}/{day}/{space_slug}/{message_slug}/message.json
    Returns the GCS prefix.
    """
    prefix = raw_prefix(space_resource_name, message_id, received_at)
    upload_json(f"{prefix}message.json", raw_message)
    logger.info("Raw chat message stored at gs://%s/%s", GCS_BUCKET, prefix)
    return prefix


def store_processed_record(record_id: str, record_dict: dict) -> str:
    """
    Store complete ChatRecord under:
      processed/{record_id}/record.json
    Returns the GCS prefix.
    """
    prefix = processed_prefix(record_id)
    upload_json(f"{prefix}record.json", record_dict)
    return prefix


def store_attachment_image(
    raw_prefix_path: str,
    attachment_id: str,
    filename: str,
    image_bytes: bytes,
    content_type: str,
) -> str:
    """
    Store an attachment image under:
      {raw_prefix}attachments/{attachment_slug}/{filename}
    Returns the GCS path (not including bucket name).
    """
    slug = attachment_id.replace("/", "_")
    safe_filename = filename or "attachment"
    gcs_path = f"{raw_prefix_path}attachments/{slug}/{safe_filename}"
    upload_bytes(gcs_path, image_bytes, content_type)
    logger.info("Attachment image stored at gs://%s/%s", GCS_BUCKET, gcs_path)
    return gcs_path


def store_attachment_ocr(
    raw_prefix_path: str,
    attachment_id: str,
    ocr_text: str,
) -> str:
    """
    Store full OCR text for an attachment under:
      {raw_prefix}attachments/{attachment_slug}/ocr.txt
    Returns the GCS path.
    """
    slug = attachment_id.replace("/", "_")
    gcs_path = f"{raw_prefix_path}attachments/{slug}/ocr.txt"
    upload_text(gcs_path, ocr_text)
    logger.info("OCR text stored at gs://%s/%s", GCS_BUCKET, gcs_path)
    return gcs_path


def update_daily_manifest(date: datetime, record_summary: dict) -> None:
    """Append a record summary to today's daily manifest JSON."""
    path = daily_manifest_path(date)
    if blob_exists(path):
        manifest = download_json(path)
    else:
        manifest = {"date": date.strftime("%Y-%m-%d"), "records": []}

    manifest["records"].append(record_summary)
    manifest["total"] = len(manifest["records"])
    upload_json(path, manifest)
