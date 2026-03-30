from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.secrets import get_chimera_api_key
from app.models.chat_record import ChimeraMeta, ChimeraResponse
from app.services import key_service

router = APIRouter()


def require_api_key(
    x_chimera_api_key: str = Header(..., alias="X-Chimera-API-Key"),
) -> str:
    """
    Validate the API key in the X-Chimera-API-Key header.

    Accepts two key types:
    1. Master key — stored in Secret Manager as 'fsu4c-chimera-api-key'.
       Returns the string "master".
    2. Generated service key — issued via POST /v1/auth/keys and stored
       (hashed) in Firestore. Returns the service_name of the registered client.

    Raises HTTP 401 if neither matches.
    """
    # 1. Master key check
    try:
        master = get_chimera_api_key()
        if x_chimera_api_key == master:
            return "master"
    except Exception:
        pass  # Secret Manager unavailable — fall through to Firestore check

    # 2. Generated key check
    record = key_service.validate_api_key(x_chimera_api_key)
    if record:
        return record["service_name"]

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing X-Chimera-API-Key",
    )


# ── API key management endpoints ──────────────────────────────────────────────

@router.post("/keys")
async def create_key(
    payload: dict,
    caller: str = Depends(require_api_key),
):
    """
    Issue a new API key for a named service.
    The plaintext key is returned ONCE — it is never stored and cannot be retrieved again.
    """
    service_name = payload.get("service_name", "").strip()
    if not service_name:
        raise HTTPException(status_code=400, detail="service_name is required")

    start = time.monotonic()
    plaintext, record = key_service.generate_api_key(
        service_name=service_name,
        description=payload.get("description", ""),
        issued_by=caller,
    )
    elapsed = int((time.monotonic() - start) * 1000)

    return ChimeraResponse(
        request_id="key-create",
        status="success",
        data={
            "key_id": record["key_id"],
            "service_name": service_name,
            "api_key": plaintext,
            "key_prefix": record["key_prefix"],
            "created_at": record["created_at"].isoformat(),
            "issued_by": caller,
            "warning": "Store this key securely — it will NOT be shown again.",
        },
        meta=ChimeraMeta(processing_time_ms=elapsed),
    )


@router.get("/keys")
async def list_keys(_: str = Depends(require_api_key)):
    """List all issued API keys. Key values are masked; only the prefix is shown."""
    start = time.monotonic()
    keys = key_service.list_api_keys()
    elapsed = int((time.monotonic() - start) * 1000)
    return ChimeraResponse(
        request_id="key-list",
        status="success",
        data={"keys": keys, "count": len(keys)},
        meta=ChimeraMeta(processing_time_ms=elapsed),
    )


@router.get("/keys/{key_id}")
async def get_key(key_id: str, _: str = Depends(require_api_key)):
    """Fetch a single key record by ID."""
    start = time.monotonic()
    key = key_service.get_api_key(key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    elapsed = int((time.monotonic() - start) * 1000)
    return ChimeraResponse(
        request_id=key_id,
        status="success",
        data=key,
        meta=ChimeraMeta(processing_time_ms=elapsed),
    )


@router.delete("/keys/{key_id}")
async def revoke_key(
    key_id: str,
    caller: str = Depends(require_api_key),
):
    """Revoke an API key. The key becomes immediately invalid."""
    start = time.monotonic()
    ok = key_service.revoke_api_key(key_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Key not found")
    elapsed = int((time.monotonic() - start) * 1000)
    return ChimeraResponse(
        request_id="key-revoke",
        status="success",
        data={"key_id": key_id, "revoked": True, "revoked_by": caller},
        meta=ChimeraMeta(processing_time_ms=elapsed),
    )
