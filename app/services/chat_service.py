from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.secrets import get_chat_credentials, get_chat_token

logger = logging.getLogger(__name__)

CHAT_SCOPES = [
    "https://www.googleapis.com/auth/chat.messages.readonly",
    "https://www.googleapis.com/auth/chat.spaces.readonly",
]


def _get_credentials() -> Credentials:
    """Build and refresh OAuth credentials for the chat account."""
    raw_token = get_chat_token()
    creds = Credentials(
        token=raw_token.get("access_token"),
        refresh_token=raw_token.get("refresh_token"),
        token_uri=raw_token.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=raw_token.get("client_id"),
        client_secret=raw_token.get("client_secret"),
        scopes=CHAT_SCOPES,
    )
    if creds.refresh_token and (not creds.valid or creds.expired):
        creds.refresh(Request())
    return creds


def _build_chat_service():
    return build("chat", "v1", credentials=_get_credentials())


def download_attachment(download_uri: str, max_size_mb: int = 50) -> bytes:
    """
    Download an UPLOADED_CONTENT attachment using the OAuth token.
    Raises ValueError if the content exceeds max_size_mb.
    Raises RuntimeError for non-200 responses.
    """
    session = AuthorizedSession(_get_credentials())
    response = session.get(download_uri, stream=True)

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to download attachment (HTTP {response.status_code}): {download_uri}"
        )

    content_length = int(response.headers.get("Content-Length", 0))
    max_bytes = max_size_mb * 1024 * 1024
    if content_length and content_length > max_bytes:
        raise ValueError(
            f"Attachment size {content_length} bytes exceeds limit of {max_size_mb} MB"
        )

    data = response.content
    if len(data) > max_bytes:
        raise ValueError(
            f"Attachment size {len(data)} bytes exceeds limit of {max_size_mb} MB"
        )

    logger.info("Downloaded attachment %d bytes from %s", len(data), download_uri)
    return data


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
        }
        if page_token:
            kwargs["pageToken"] = page_token

        try:
            result = service.spaces().messages().list(**kwargs).execute()
        except HttpError as exc:
            logger.error(
                "Chat API error listing messages for %s (status %s): %s",
                space_resource_name, exc.status_code, exc,
            )
            raise

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
