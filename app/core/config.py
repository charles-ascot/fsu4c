from __future__ import annotations

import os
from pydantic import BaseModel, Field

GCP_PROJECT = "chimera-v4"
GCP_REGION = "europe-west2"
CLOUD_RUN_SERVICE = "fsu4c"
FSU_NAME = "fsu4c"
FSU_VERSION = "1.0.0"
API_VERSION = "1.0"

CHAT_ACCOUNT = os.environ.get("CHAT_INGEST_ACCOUNT", "cloud@ascotwm.com")
PUBSUB_TOPIC = "fsu4c-trigger"
PUBSUB_SUBSCRIPTION = "fsu4c-sub"

GCS_BUCKET = "chimera-ops-chat-raw"

FIRESTORE_COLLECTION = "fsu4c-intelligence"
FIRESTORE_SPACES_COLLECTION = "fsu4c-spaces"
FIRESTORE_API_KEYS_COLLECTION = "fsu4c-api-keys"
FIRESTORE_CONFIG_DOC = "fsu4c-config"

CHIMERA_DOMAIN_HINTS = [
    "horse racing",
    "lay betting",
    "betfair",
    "form guide",
    "stake management",
    "signal intelligence",
    "spread control",
    "market data",
    "racing tips",
    "trading strategy",
]


class ProcessingConfig(BaseModel):
    ignore_senders: list[str] = Field(
        default_factory=list,
        description="Sender user IDs or email addresses to skip",
    )
    ignore_spaces: list[str] = Field(
        default_factory=list,
        description="Space resource names to skip (e.g. spaces/AAAA1234)",
    )
    poll_interval_minutes: int = Field(
        default=5,
        description="Minutes between Chat polls — should match Cloud Scheduler interval",
    )
    max_attachment_size_mb: int = Field(
        default=50,
        description="Maximum attachment size in MB to download and store",
    )
    cloud_run_timeout_seconds: int = Field(
        default=300,
        description="Cloud Run request timeout",
    )
    extra_domain_hints: list[str] = Field(
        default_factory=list,
        description="Additional domain hints passed downstream for AI processing",
    )


CONFIG_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "ignore_senders": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Sender IDs or emails to skip",
        },
        "ignore_spaces": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Space resource names to skip",
        },
        "poll_interval_minutes": {"type": "integer"},
        "max_attachment_size_mb": {"type": "integer"},
        "cloud_run_timeout_seconds": {"type": "integer"},
        "extra_domain_hints": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "additionalProperties": False,
}
