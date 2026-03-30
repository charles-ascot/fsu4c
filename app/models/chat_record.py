from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class RecordStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    complete = "complete"
    failed = "failed"
    skipped = "skipped"


class SpaceType(str, Enum):
    space = "SPACE"
    group_chat = "GROUP_CHAT"
    direct_message = "DIRECT_MESSAGE"
    unknown = "UNKNOWN"


class ChatAttachmentRecord(BaseModel):
    attachment_id: str
    filename: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    gcs_path: Optional[str] = None
    download_uri: Optional[str] = None
    source: Optional[str] = None   # UPLOADED_CONTENT | DRIVE_FILE | LINK
    processing_status: str = "metadata_only"


class ChatRecord(BaseModel):
    # Identity
    record_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: RecordStatus = RecordStatus.pending
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Chat source metadata
    message_id: str                      # Full resource name: spaces/{space}/messages/{msg}
    space_id: str                        # Internal FSU4C space registry ID
    space_resource_name: str             # Chat API resource name: spaces/{space}
    space_display_name: str              # Human-readable name
    space_type: SpaceType = SpaceType.unknown
    thread_id: Optional[str] = None     # Thread resource name
    sender_id: str                       # Sender user resource name
    sender_name: str                     # Display name
    sender_email: Optional[str] = None  # Sender email if available
    message_text: str = ""

    received_at: datetime

    # Attachments
    attachments: list[ChatAttachmentRecord] = Field(default_factory=list)

    # GCS paths
    gcs_raw_prefix: Optional[str] = None
    gcs_processed_prefix: Optional[str] = None

    # Processing metadata
    processing_error: Optional[str] = None
    processing_time_ms: Optional[int] = None

    def to_firestore_dict(self) -> dict:
        data = self.model_dump(mode="json")
        data["created_at"] = self.created_at
        data["updated_at"] = self.updated_at
        data["received_at"] = self.received_at
        return data

    @classmethod
    def from_firestore_dict(cls, data: dict) -> "ChatRecord":
        for field in ("created_at", "updated_at", "received_at"):
            if hasattr(data.get(field), "timestamp"):
                data[field] = data[field].replace(tzinfo=None)
        return cls(**data)


class ChatSpace(BaseModel):
    space_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    space_resource_name: str         # e.g. spaces/AAAA1234
    display_name: str
    space_type: SpaceType = SpaceType.unknown
    description: Optional[str] = None
    active: bool = True
    added_at: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0
    last_received_at: Optional[datetime] = None


class ChimeraMeta(BaseModel):
    processing_time_ms: int = 0
    version: str = "1.0.0"


class ChimeraResponse(BaseModel):
    chimera_version: str = "1.0"
    request_id: str
    fsu: str = "chimera-fsu4c-chat-ingest"
    status: str = "success"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: dict = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    meta: ChimeraMeta = Field(default_factory=ChimeraMeta)
