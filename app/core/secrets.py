from __future__ import annotations

import json
from functools import lru_cache

from google.cloud import secretmanager

_client: secretmanager.SecretManagerServiceClient | None = None


def _get_client() -> secretmanager.SecretManagerServiceClient:
    global _client
    if _client is None:
        _client = secretmanager.SecretManagerServiceClient()
    return _client


def get_secret(secret_id: str, project_id: str = "chimera-v4", version: str = "latest") -> str:
    client = _get_client()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("utf-8")


def get_secret_json(secret_id: str, project_id: str = "chimera-v4", version: str = "latest") -> dict:
    return json.loads(get_secret(secret_id, project_id, version))


@lru_cache(maxsize=None)
def get_chimera_api_key() -> str:
    return get_secret("fsu4c-chimera-api-key")


@lru_cache(maxsize=None)
def get_chat_credentials() -> dict:
    return get_secret_json("chat-oauth-credentials")


@lru_cache(maxsize=None)
def get_chat_token() -> dict:
    return get_secret_json("chat-token")
