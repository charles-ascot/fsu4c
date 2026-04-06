from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.config import GCS_BUCKET, ProcessingConfig
from app.models.chat_record import (
    ChatAttachmentRecord,
    ChatRecord,
    ChimeraMeta,
    ChimeraResponse,
    IntelligenceClassification,
    RecordStatus,
)
from app.routers.auth import require_api_key
from app.routers.config import get_current_config
from app.services import (
    chat_service,
    firestore_service,
    intelligence_service,
    storage_service,
    vision_service,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Pub/Sub push receiver ──────────────────────────────────────────────────────

@router.post("/pubsub-push", status_code=status.HTTP_204_NO_CONTENT)
async def pubsub_push(request: Request):
    """
    Cloud Pub/Sub push endpoint — triggered by Cloud Scheduler on a regular
    interval (default: every 5 minutes).  The message payload is not used;
    the trigger alone causes FSU4C to poll all registered Chat spaces for
    new messages since the last poll cursor.
    """
    try:
        await request.json()
    except Exception:
        pass  # Accept any payload — we only need the trigger

    try:
        config = get_current_config()
    except Exception as exc:
        logger.error("Failed to load config — using defaults: %s", exc, exc_info=True)
        config = ProcessingConfig()

    try:
        _poll_all_spaces(config)
    except Exception as exc:
        logger.error("Poll cycle failed: %s", exc, exc_info=True)


# ── Manual triggers ────────────────────────────────────────────────────────────

@router.post("/manual")
async def manual_poll(
    payload: dict,
    _: str = Depends(require_api_key),
):
    """
    Manually trigger a poll for a specific space, or all spaces if no
    space_resource_name is provided.  Optionally pass since_iso to override
    the poll cursor (e.g. "2026-03-01T00:00:00").
    """
    start = time.monotonic()
    config = get_current_config()

    space_resource_name = payload.get("space_resource_name")
    since_iso = payload.get("since_iso")

    since: datetime | None = None
    if since_iso:
        try:
            since = datetime.fromisoformat(since_iso)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid since_iso format — use ISO 8601")

    if space_resource_name:
        space = firestore_service.get_space_by_resource_name(space_resource_name)
        if not space:
            raise HTTPException(status_code=404, detail="Space not registered")
        if since is None:
            since = firestore_service.get_last_poll_time() or (
                datetime.utcnow() - timedelta(hours=1)
            )
        count = _poll_space(space, since, config)
        processed = count
    else:
        processed = _poll_all_spaces(config, override_since=since)

    elapsed = int((time.monotonic() - start) * 1000)
    return ChimeraResponse(
        request_id="manual-poll",
        status="success",
        data={"messages_processed": processed},
        meta=ChimeraMeta(processing_time_ms=elapsed),
    )


@router.get("/queue")
async def get_queue(_: str = Depends(require_api_key)):
    """View records currently in pending/processing status."""
    pending = firestore_service.get_pending_records()
    return ChimeraResponse(
        request_id="queue-query",
        status="success",
        data={
            "pending_count": len(pending),
            "records": [
                {
                    "record_id": r.record_id,
                    "message_id": r.message_id,
                    "space_display_name": r.space_display_name,
                    "sender_name": r.sender_name,
                    "received_at": r.received_at.isoformat(),
                    "status": r.status.value,
                }
                for r in pending
            ],
        },
        meta=ChimeraMeta(),
    )


# ── Core poll pipeline ─────────────────────────────────────────────────────────

def _poll_all_spaces(
    config: ProcessingConfig,
    override_since: datetime | None = None,
) -> int:
    """
    Poll all active registered spaces for new messages.
    Returns the total number of messages processed.
    """
    spaces = firestore_service.list_active_spaces()
    if not spaces:
        logger.info("No active spaces registered — nothing to poll")
        return 0

    last_poll = override_since or firestore_service.get_last_poll_time()
    now = datetime.utcnow()

    if not last_poll:
        # First run — look back slightly further than the poll interval
        last_poll = now - timedelta(minutes=config.poll_interval_minutes + 5)

    logger.info("Polling %d spaces since %s", len(spaces), last_poll.isoformat())

    total = 0
    for space in spaces:
        if space.space_resource_name in config.ignore_spaces:
            logger.info("Skipping space %s — in ignore list", space.space_resource_name)
            continue
        try:
            total += _poll_space(space, last_poll, config)
        except Exception as exc:
            logger.error(
                "Failed to poll space %s: %s",
                space.space_resource_name, exc, exc_info=True,
            )

    # Advance the poll cursor AFTER all spaces complete
    if override_since is None:
        firestore_service.set_last_poll_time(now)

    logger.info("Poll cycle complete — %d messages processed", total)
    return total


def _poll_space(space, since: datetime, config: ProcessingConfig) -> int:
    """Poll a single space and process all new messages. Returns count processed."""
    messages = chat_service.list_messages_since(space.space_resource_name, since=since)
    count = 0
    for msg in messages:
        parsed = chat_service.parse_chat_message(msg)
        try:
            processed = _process_message(parsed, space, config)
            if processed:
                count += 1
        except Exception as exc:
            logger.error(
                "Failed to process message %s: %s",
                parsed.get("message_id"), exc, exc_info=True,
            )
    return count


def _process_message(
    parsed: dict,
    space,
    config: ProcessingConfig,
) -> bool:
    """
    Process a single parsed Chat message.
    Returns True if a new record was created, False if skipped/duplicate.

    Pipeline:
    1. Idempotency check
    2. Skip check (sender filters)
    3. Create skeleton ChatRecord → write to Firestore (status=processing)
    4. Store raw message JSON to GCS
    5. Store attachment metadata
    6. Store processed record to GCS
    7. Update Firestore record (status=complete)
    8. Update space stats + daily manifest
    """
    message_id = parsed["message_id"]

    # 1. Idempotency — only skip if a completed record exists
    existing = firestore_service.get_existing_record_status(message_id)
    if existing == RecordStatus.complete.value:
        logger.debug("Message %s already processed — skipping", message_id)
        return False
    if existing is not None:
        # Stale skeleton from a previous failed attempt — remove it so we can retry
        firestore_service.delete_record_by_message_id(message_id)
        logger.info("Cleared stale %s record for %s — retrying", existing, message_id)

    # 2. Skip checks
    sender_id = parsed.get("sender_id", "")
    sender_email = parsed.get("sender_email", "")
    if sender_id in config.ignore_senders or (
        sender_email and sender_email in config.ignore_senders
    ):
        logger.info("Skipping message %s — sender in ignore list", message_id)
        return False

    start = time.monotonic()

    # 3. Create skeleton record (includes raw_payload)
    record = ChatRecord(
        message_id=message_id,
        space_id=space.space_id,
        space_resource_name=space.space_resource_name,
        space_display_name=space.display_name,
        space_type=space.space_type,
        thread_id=parsed.get("thread_id"),
        sender_id=sender_id,
        sender_name=parsed.get("sender_name", ""),
        sender_email=sender_email or None,
        message_text=parsed.get("message_text", ""),
        received_at=parsed["received_at"],
        status=RecordStatus.processing,
        raw_payload=parsed.get("raw"),
    )
    firestore_service.create_record(record)

    # 4. Store raw message to GCS
    gcs_raw_prefix = storage_service.store_raw_message(
        message_id=message_id,
        space_resource_name=space.space_resource_name,
        received_at=parsed["received_at"],
        raw_message=parsed["raw"],
    )
    record.gcs_raw_prefix = gcs_raw_prefix

    # 5. Attachments — download images, OCR, store to GCS
    for att_data in parsed.get("attachments", []):
        att = ChatAttachmentRecord(
            attachment_id=att_data.get("attachment_id", ""),
            filename=att_data.get("filename"),
            content_type=att_data.get("content_type"),
            download_uri=att_data.get("download_uri"),
            source=att_data.get("source"),
            processing_status="metadata_only",
        )
        source = att_data.get("source", "")
        content_type = att_data.get("content_type", "") or ""
        download_uri = att_data.get("download_uri", "")

        if source == "UPLOADED_CONTENT" and content_type.startswith("image/") and download_uri:
            try:
                image_bytes = chat_service.download_attachment(
                    download_uri, max_size_mb=config.max_attachment_size_mb
                )
                att.size_bytes = len(image_bytes)
                gcs_path = storage_service.store_attachment_image(
                    raw_prefix_path=gcs_raw_prefix,
                    attachment_id=att.attachment_id,
                    filename=att.filename or "attachment.png",
                    image_bytes=image_bytes,
                    content_type=content_type,
                )
                att.gcs_path = gcs_path
                gcs_uri = f"gs://{GCS_BUCKET}/{gcs_path}"
                ocr_text, ocr_confidence = vision_service.ocr_from_gcs_uri(gcs_uri)
                att.ocr_text = ocr_text
                att.ocr_confidence = ocr_confidence
                att.ocr_processed_at = datetime.utcnow()
                # Store full OCR text to GCS (may be truncated in Firestore)
                if ocr_text:
                    storage_service.store_attachment_ocr(
                        raw_prefix_path=gcs_raw_prefix,
                        attachment_id=att.attachment_id,
                        ocr_text=ocr_text,
                    )
                att.processing_status = "ocr_complete"
                logger.info(
                    "Attachment OCR complete for message %s — %d chars extracted",
                    message_id, len(ocr_text),
                )
            except Exception as exc:
                logger.error(
                    "Attachment processing failed for message %s: %s",
                    message_id, exc, exc_info=True,
                )
                att.processing_status = "failed"
        elif source == "DRIVE_FILE":
            logger.warning(
                "Skipping DRIVE_FILE attachment for message %s — Drive scope not available",
                message_id,
            )
            att.processing_status = "skipped_drive_file"

        record.attachments.append(att)

    # 5b. Intelligence classification
    classification = {}
    try:
        classification = intelligence_service.classify_record(
            text=parsed.get("message_text", ""),
            keyword_categories=config.keyword_categories,
            cloud_mention_triggers=config.cloud_mention_triggers,
        )
        record.intelligence = IntelligenceClassification(**classification)
    except Exception as exc:
        logger.error(
            "Intelligence classification failed for message %s: %s",
            message_id, exc, exc_info=True,
        )
        # Continue without classification — don't block the record

    # 6. Store processed record to GCS
    try:
        gcs_processed_prefix = storage_service.store_processed_record(
            record.record_id, record.model_dump(mode="json")
        )
        record.gcs_processed_prefix = gcs_processed_prefix
    except Exception as exc:
        logger.error(
            "Failed to store processed record %s to GCS: %s",
            record.record_id, exc, exc_info=True,
        )

    # 7. Finalise
    record.status = RecordStatus.complete
    record.processing_time_ms = int((time.monotonic() - start) * 1000)
    firestore_service.update_record(record)

    # 8. Stats + manifest
    try:
        firestore_service.increment_space_message_count(space.space_resource_name)
        storage_service.update_daily_manifest(
            parsed["received_at"],
            {
                "record_id": record.record_id,
                "message_id": message_id,
                "space_display_name": space.display_name,
                "sender_name": parsed.get("sender_name", ""),
                "status": record.status.value,
                "attachment_count": len(record.attachments),
                "record_type": classification.get("record_type", "observation"),
                "keyword_hits": classification.get("keyword_hits", 0),
            },
        )
    except Exception as exc:
        logger.error(
            "Failed to update stats/manifest for %s: %s",
            message_id, exc, exc_info=True,
        )

    logger.info(
        "Processed Chat message %s → record %s (%dms)",
        message_id, record.record_id, record.processing_time_ms,
    )
    return True
