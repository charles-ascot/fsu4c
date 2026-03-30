from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from google.cloud import firestore

from app.core.config import (
    FIRESTORE_COLLECTION,
    FIRESTORE_SPACES_COLLECTION,
    FIRESTORE_CONFIG_DOC,
    GCP_PROJECT,
    ProcessingConfig,
)
from app.models.chat_record import ChatRecord, ChatSpace, RecordStatus

logger = logging.getLogger(__name__)

_client: firestore.Client | None = None


def _db() -> firestore.Client:
    global _client
    if _client is None:
        _client = firestore.Client(project=GCP_PROJECT)
    return _client


def _records() -> firestore.CollectionReference:
    return _db().collection(FIRESTORE_COLLECTION)


def _spaces() -> firestore.CollectionReference:
    return _db().collection(FIRESTORE_SPACES_COLLECTION)


def _config_ref() -> firestore.DocumentReference:
    return _db().collection("chimera-fsu-config").document(FIRESTORE_CONFIG_DOC)


# ── Idempotency ───────────────────────────────────────────────────────────────

def message_already_processed(message_id: str) -> bool:
    query = _records().where("message_id", "==", message_id).limit(1).stream()
    return any(True for _ in query)


def get_record_by_message_id(message_id: str) -> Optional[ChatRecord]:
    query = _records().where("message_id", "==", message_id).limit(1).stream()
    for doc in query:
        return ChatRecord.from_firestore_dict(doc.to_dict())
    return None


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_record(record: ChatRecord) -> str:
    doc_ref = _records().document(record.record_id)
    doc_ref.set(record.to_firestore_dict())
    logger.info("Created record %s for message %s", record.record_id, record.message_id)
    return record.record_id


def update_record(record: ChatRecord) -> None:
    record.updated_at = datetime.utcnow()
    _records().document(record.record_id).set(record.to_firestore_dict())


def get_record(record_id: str) -> Optional[ChatRecord]:
    doc = _records().document(record_id).get()
    if not doc.exists:
        return None
    return ChatRecord.from_firestore_dict(doc.to_dict())


def query_records(
    space_id: Optional[str] = None,
    sender: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ChatRecord]:
    query = _records()

    if status:
        query = query.where("status", "==", status)
    if space_id:
        query = query.where("space_id", "==", space_id)
    if sender:
        # Match on email or sender_id
        query = query.where("sender_email", "==", sender.lower())

    query = query.order_by("received_at", direction=firestore.Query.DESCENDING)
    query = query.limit(limit + offset)

    results = []
    for i, doc in enumerate(query.stream()):
        if i < offset:
            continue
        results.append(ChatRecord.from_firestore_dict(doc.to_dict()))

    return results


def get_metrics() -> dict:
    all_docs = _records().stream()
    total = 0
    by_status: dict[str, int] = {}
    by_space: dict[str, int] = {}

    for doc in all_docs:
        data = doc.to_dict()
        total += 1
        s = data.get("status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1
        sp = data.get("space_display_name", "unknown")
        by_space[sp] = by_space.get(sp, 0) + 1

    return {
        "total_records": total,
        "by_status": by_status,
        "by_space": by_space,
    }


def get_pending_records(limit: int = 100) -> list[ChatRecord]:
    query = (
        _records()
        .where("status", "==", RecordStatus.pending.value)
        .order_by("received_at")
        .limit(limit)
    )
    return [ChatRecord.from_firestore_dict(d.to_dict()) for d in query.stream()]


# ── Poll cursor ───────────────────────────────────────────────────────────────

def get_last_poll_time() -> Optional[datetime]:
    doc = _db().collection("chimera-fsu-system").document("fsu4c-poll").get()
    if doc.exists:
        val = doc.to_dict().get("last_poll_time")
        if hasattr(val, "replace"):
            return val.replace(tzinfo=None)
    return None


def set_last_poll_time(t: datetime) -> None:
    _db().collection("chimera-fsu-system").document("fsu4c-poll").set(
        {"last_poll_time": t, "updated_at": datetime.utcnow()}
    )


# ── Spaces ────────────────────────────────────────────────────────────────────

def list_spaces() -> list[ChatSpace]:
    return [
        ChatSpace(**d.to_dict())
        for d in _spaces().order_by("added_at").stream()
    ]


def list_active_spaces() -> list[ChatSpace]:
    return [
        ChatSpace(**d.to_dict())
        for d in _spaces().where("active", "==", True).stream()
    ]


def create_space(space: ChatSpace) -> str:
    _spaces().document(space.space_id).set(space.model_dump(mode="json"))
    return space.space_id


def get_space(space_id: str) -> Optional[ChatSpace]:
    doc = _spaces().document(space_id).get()
    if not doc.exists:
        return None
    return ChatSpace(**doc.to_dict())


def get_space_by_resource_name(space_resource_name: str) -> Optional[ChatSpace]:
    query = (
        _spaces()
        .where("space_resource_name", "==", space_resource_name)
        .limit(1)
        .stream()
    )
    for doc in query:
        return ChatSpace(**doc.to_dict())
    return None


def delete_space(space_id: str) -> bool:
    doc_ref = _spaces().document(space_id)
    if not doc_ref.get().exists:
        return False
    doc_ref.delete()
    return True


def increment_space_message_count(space_resource_name: str) -> None:
    query = (
        _spaces()
        .where("space_resource_name", "==", space_resource_name)
        .limit(1)
        .stream()
    )
    for doc in query:
        doc.reference.update(
            {
                "message_count": firestore.Increment(1),
                "last_received_at": datetime.utcnow(),
            }
        )
        return


# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> ProcessingConfig:
    doc = _config_ref().get()
    if doc.exists:
        return ProcessingConfig(**doc.to_dict())
    return ProcessingConfig()


def save_config(config: ProcessingConfig) -> None:
    _config_ref().set(config.model_dump())
