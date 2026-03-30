from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from app.core.config import CONFIG_JSON_SCHEMA, ProcessingConfig
from app.models.chat_record import ChimeraMeta, ChimeraResponse
from app.routers.auth import require_api_key
from app.services import firestore_service

router = APIRouter()

_config_cache: ProcessingConfig | None = None


def get_current_config() -> ProcessingConfig:
    global _config_cache
    if _config_cache is None:
        _config_cache = firestore_service.load_config()
    return _config_cache


def _invalidate_config_cache() -> None:
    global _config_cache
    _config_cache = None


@router.get("")
async def get_config(_: str = Depends(require_api_key)):
    start = time.monotonic()
    config = get_current_config()
    elapsed = int((time.monotonic() - start) * 1000)
    return ChimeraResponse(
        request_id="config-get",
        status="success",
        data=config.model_dump(),
        meta=ChimeraMeta(processing_time_ms=elapsed),
    )


@router.put("")
async def update_config(
    payload: dict,
    _: str = Depends(require_api_key),
):
    start = time.monotonic()
    current = get_current_config()
    updated_data = {**current.model_dump(), **payload}
    new_config = ProcessingConfig(**updated_data)
    firestore_service.save_config(new_config)
    _invalidate_config_cache()
    elapsed = int((time.monotonic() - start) * 1000)
    return ChimeraResponse(
        request_id="config-update",
        status="success",
        data=new_config.model_dump(),
        meta=ChimeraMeta(processing_time_ms=elapsed),
    )


@router.get("/schema")
async def get_config_schema(_: str = Depends(require_api_key)):
    return ChimeraResponse(
        request_id="config-schema",
        status="success",
        data={"schema": CONFIG_JSON_SCHEMA},
        meta=ChimeraMeta(),
    )
