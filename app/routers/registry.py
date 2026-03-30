from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.chat_record import ChimeraMeta, ChimeraResponse
from app.routers.auth import require_api_key
from app.services import firestore_service

router = APIRouter()


@router.get("")
async def query_registry(
    space_id: Optional[str] = Query(None, description="Filter by FSU4C space registry ID"),
    sender: Optional[str] = Query(None, description="Filter by sender email"),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: str = Depends(require_api_key),
):
    start = time.monotonic()
    records = firestore_service.query_records(
        space_id=space_id,
        sender=sender,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    elapsed = int((time.monotonic() - start) * 1000)

    return ChimeraResponse(
        request_id="registry-query",
        status="success",
        data={
            "records": [r.model_dump(mode="json") for r in records],
            "count": len(records),
            "limit": limit,
            "offset": offset,
        },
        meta=ChimeraMeta(processing_time_ms=elapsed),
    )


@router.get("/metrics")
async def get_metrics(_: str = Depends(require_api_key)):
    start = time.monotonic()
    metrics = firestore_service.get_metrics()
    elapsed = int((time.monotonic() - start) * 1000)
    return ChimeraResponse(
        request_id="registry-metrics",
        status="success",
        data=metrics,
        meta=ChimeraMeta(processing_time_ms=elapsed),
    )


@router.get("/{record_id}")
async def get_record(
    record_id: str,
    _: str = Depends(require_api_key),
):
    start = time.monotonic()
    record = firestore_service.get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    elapsed = int((time.monotonic() - start) * 1000)
    return ChimeraResponse(
        request_id=record_id,
        status="success",
        data=record.model_dump(mode="json"),
        meta=ChimeraMeta(processing_time_ms=elapsed),
    )
