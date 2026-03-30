from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException

from app.models.chat_record import ChatSpace, ChimeraMeta, ChimeraResponse, SpaceType
from app.routers.auth import require_api_key
from app.services import chat_service, firestore_service

router = APIRouter()


def _map_space_type(raw: str) -> SpaceType:
    mapping = {
        "SPACE": SpaceType.space,
        "GROUP_CHAT": SpaceType.group_chat,
        "DIRECT_MESSAGE": SpaceType.direct_message,
    }
    return mapping.get(raw.upper(), SpaceType.unknown)


@router.get("")
async def list_spaces(_: str = Depends(require_api_key)):
    """List all registered Chat spaces."""
    start = time.monotonic()
    spaces = firestore_service.list_spaces()
    elapsed = int((time.monotonic() - start) * 1000)
    return ChimeraResponse(
        request_id="spaces-list",
        status="success",
        data={
            "spaces": [s.model_dump(mode="json") for s in spaces],
            "count": len(spaces),
        },
        meta=ChimeraMeta(processing_time_ms=elapsed),
    )


@router.post("")
async def register_space(
    payload: dict,
    _: str = Depends(require_api_key),
):
    """
    Register a Google Chat space for monitoring.
    Provide the Chat API resource name (e.g. 'spaces/AAAA1234').
    FSU4C will fetch the space details from the Chat API and begin polling it.
    """
    space_resource_name = payload.get("space_resource_name", "").strip()
    if not space_resource_name:
        raise HTTPException(status_code=400, detail="space_resource_name is required")

    # Prevent duplicate registrations
    existing = firestore_service.get_space_by_resource_name(space_resource_name)
    if existing:
        return ChimeraResponse(
            request_id="space-register",
            status="success",
            data={
                **existing.model_dump(mode="json"),
                "note": "Space already registered",
            },
            meta=ChimeraMeta(),
        )

    # Fetch live details from Chat API
    start = time.monotonic()
    try:
        space_data = chat_service.get_space(space_resource_name)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not fetch space from Chat API: {exc}",
        )

    space = ChatSpace(
        space_resource_name=space_resource_name,
        display_name=space_data.get("displayName") or space_resource_name,
        space_type=_map_space_type(space_data.get("spaceType", "UNKNOWN")),
        description=payload.get("description", ""),
    )
    space_id = firestore_service.create_space(space)
    elapsed = int((time.monotonic() - start) * 1000)

    return ChimeraResponse(
        request_id="space-register",
        status="success",
        data={**space.model_dump(mode="json"), "space_id": space_id},
        meta=ChimeraMeta(processing_time_ms=elapsed),
    )


@router.post("/discover")
async def discover_spaces(_: str = Depends(require_api_key)):
    """
    Query the Chat API for all spaces that chimera.data.in is a member of.
    Returns the raw list — use POST /v1/spaces to register individual spaces.
    """
    start = time.monotonic()
    try:
        raw_spaces = chat_service.list_spaces()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Chat API error: {exc}")

    elapsed = int((time.monotonic() - start) * 1000)
    return ChimeraResponse(
        request_id="spaces-discover",
        status="success",
        data={
            "available_spaces": [
                {
                    "space_resource_name": s.get("name"),
                    "display_name": s.get("displayName", ""),
                    "space_type": s.get("spaceType", "UNKNOWN"),
                    "already_registered": (
                        firestore_service.get_space_by_resource_name(s.get("name", "")) is not None
                    ),
                }
                for s in raw_spaces
            ],
            "count": len(raw_spaces),
        },
        meta=ChimeraMeta(processing_time_ms=elapsed),
    )


@router.delete("/{space_id}")
async def deregister_space(
    space_id: str,
    _: str = Depends(require_api_key),
):
    """Remove a space from the monitoring registry."""
    start = time.monotonic()
    deleted = firestore_service.delete_space(space_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Space not found")
    elapsed = int((time.monotonic() - start) * 1000)
    return ChimeraResponse(
        request_id="space-deregister",
        status="success",
        data={"space_id": space_id, "deleted": True},
        meta=ChimeraMeta(processing_time_ms=elapsed),
    )
