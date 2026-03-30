from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.secrets import get_chat_credentials, get_chat_token

logger = logging.getLogger(__name__)

CHAT_SCOPES = [
    "https://www.googleapis.com/auth/chat.messages.readonly",
    "https://www.googleapis.com/auth/chat.spaces.readonly",
]


def _build_chat_service():
    raw_creds = get_chat_credentials()
    raw_token = get_chat_token()

    creds = Credentials(
        token=raw_token.get("token"),
        refresh_token=raw_token.get("refresh_token"),
        token_uri=raw_creds.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=raw_creds.get("client_id"),
        client_secret=raw_creds.get("client_secret"),
        scopes=CHAT_SCOPES,
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build("chat", "v1", credentials=creds)


def list_spaces() -> list[dict]:
    """List all Chat spaces the account is a member of."""
    service = _build_chat_service()
    spaces = []
    page_token = None
    while True:
        kwargs: dict = {"pageSize": 100}
        if page_token:
            kwargs["pageToken"] = page_token
        result = service.spaces().list(**kwargs).execute()
        spaces.extend(result.get("spaces", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    logger.info("Discovered %d Chat spaces", len(spaces))
    return spaces


def get_space(space_resource_name: str) -> dict:
    """Fetch a single space's details from the Chat API."""
    service = _build_chat_service()
    return service.spaces().get(name=space_resource_name).execute()


def list_messages_since(
    space_resource_name: str,
    since: datetime,
    page_size: int = 100,
) -> list[dict]:
    """
    Fetch all messages in a space created strictly after `since`.
    Paginates automatically. Returns raw Chat API message dicts.
    """
    service = _build_chat_service()
    # Chat API filter: createTime must be a RFC 3339 UTC string
    filter_str = f'createTime > "{since.strftime("%Y-%m-%dT%H:%M:%S")}Z"'
    messages = []
    page_token = None

    while True:
        kwargs: dict = {
            "parent": space_resource_name,
            "pageSize": page_size,
            "filter": filter_str,
            "orderBy": "createTime asc",
        }
        if page_token:
            kwargs["pageToken"] = page_token

        try:
            result = service.spaces().messages().list(**kwargs).execute()
        except HttpError as exc:
            logger.warning(
                "Chat API error listing messages for %s: %s",
                space_resource_name, exc,
            )
            break

        messages.extend(result.get("messages", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break

    logger.info(
        "Fetched %d messages from %s since %s",
        len(messages), space_resource_name, since.isoformat(),
    )
    return messages


def parse_chat_message(msg: dict) -> dict:
    """
    Normalise a raw Chat API message dict into a flat structure
    ready for ChatRecord creation.
    """
    name = msg.get("name", "")           # spaces/{space}/messages/{msg}
    parts = name.split("/")
    space_resource_name = f"spaces/{parts[1]}" if len(parts) >= 2 else ""

    thread_name: Optional[str] = msg.get("thread", {}).get("name")

    sender = msg.get("sender", {})
    sender_id: str = sender.get("name", "")
    sender_display: str = sender.get("displayName", "")
    sender_email: Optional[str] = sender.get("email")

    create_time: str = msg.get("createTime", "")
    try:
        received_at = datetime.fromisoformat(
            create_time.replace("Z", "+00:00")
        ).replace(tzinfo=None)
    except Exception:
        received_at = datetime.utcnow()

    text: str = msg.get("text", "") or msg.get("formattedText", "") or ""

    # Normalise attachments
    attachments = []
    for att in msg.get("attachment", []):
        attachments.append({
            "attachment_id": att.get("name", ""),
            "filename": att.get("contentName"),
            "content_type": att.get("contentType"),
            "download_uri": att.get("downloadUri"),
            "source": att.get("source"),  # UPLOADED_CONTENT | DRIVE_FILE | LINK
        })

    return {
        "message_id": name,
        "space_resource_name": space_resource_name,
        "thread_id": thread_name,
        "sender_id": sender_id,
        "sender_name": sender_display,
        "sender_email": sender_email,
        "message_text": text,
        "received_at": received_at,
        "attachments": attachments,
        "raw": msg,
    }
