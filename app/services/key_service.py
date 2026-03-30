from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import datetime
from typing import Optional

from google.cloud import firestore

from app.core.config import FIRESTORE_API_KEYS_COLLECTION, GCP_PROJECT

logger = logging.getLogger(__name__)

_client: firestore.Client | None = None


def _db() -> firestore.Client:
    global _client
    if _client is None:
        _client = firestore.Client(project=GCP_PROJECT)
    return _client


def _keys() -> firestore.CollectionReference:
    return _db().collection(FIRESTORE_API_KEYS_COLLECTION)


def generate_api_key(
    service_name: str,
    description: str = "",
    issued_by: str = "api",
) -> tuple[str, dict]:
    """
    Generate a new API key for a named service.
    Returns (plaintext_key, key_record).
    The plaintext key is returned ONCE — only the SHA-256 hash is stored.
    """
    key_id = str(uuid.uuid4())
    plaintext = f"fsu4c-{secrets.token_hex(32)}"
    key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    key_prefix = plaintext[:14] + "..."   # Safe display prefix

    record = {
        "key_id": key_id,
        "service_name": service_name,
        "key_hash": key_hash,
        "key_prefix": key_prefix,
        "description": description,
        "issued_by": issued_by,
        "created_at": datetime.utcnow(),
        "last_used_at": None,
        "active": True,
    }

    _keys().document(key_id).set(record)
    logger.info("API key issued: key_id=%s service=%s issued_by=%s", key_id, service_name, issued_by)
    return plaintext, record


def validate_api_key(key: str) -> Optional[dict]:
    """
    Validate a generated API key.
    Returns the key record (with service_name) if valid, None if invalid/revoked.
    Updates last_used_at on success.
    """
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    query = (
        _keys()
        .where("key_hash", "==", key_hash)
        .where("active", "==", True)
        .limit(1)
        .stream()
    )
    for doc in query:
        record = doc.to_dict()
        doc.reference.update({"last_used_at": datetime.utcnow()})
        return record
    return None


def list_api_keys() -> list[dict]:
    """List all API keys. key_hash is excluded from the response."""
    docs = _keys().order_by("created_at", direction=firestore.Query.DESCENDING).stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        data.pop("key_hash", None)     # Never expose hash
        # Serialise datetimes
        for field in ("created_at", "last_used_at"):
            val = data.get(field)
            if hasattr(val, "isoformat"):
                data[field] = val.isoformat()
        results.append(data)
    return results


def get_api_key(key_id: str) -> Optional[dict]:
    doc = _keys().document(key_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data.pop("key_hash", None)
    for field in ("created_at", "last_used_at"):
        val = data.get(field)
        if hasattr(val, "isoformat"):
            data[field] = val.isoformat()
    return data


def revoke_api_key(key_id: str) -> bool:
    doc_ref = _keys().document(key_id)
    if not doc_ref.get().exists:
        return False
    doc_ref.update({"active": False, "revoked_at": datetime.utcnow()})
    logger.info("API key revoked: key_id=%s", key_id)
    return True
