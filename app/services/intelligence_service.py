from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def detect_cloud_mention(
    text: str,
    triggers: list[str],
) -> tuple[bool, Optional[str]]:
    """
    Detect if a message is a direct instruction to the cloud account.
    Returns (is_instruction, instruction_text).
    """
    if not text:
        return (False, None)

    lower = text.lower().strip()
    for trigger in triggers:
        t = trigger.lower()
        if lower.startswith(t):
            instruction_text = text[len(trigger):].strip().lstrip(",: -").strip()
            return (True, instruction_text or text)
        if f" {t} " in f" {lower} " or f" {t}" in lower:
            idx = lower.find(t)
            instruction_text = text[idx + len(trigger):].strip().lstrip(",: -").strip()
            return (True, instruction_text or text)

    return (False, None)


def detect_keywords(
    text: str,
    keyword_categories: dict[str, list[str]],
) -> tuple[dict[str, list[str]], int]:
    """
    Match text against keyword categories.
    Returns (matched_keywords dict, total_hit_count).
    """
    if not text:
        return ({}, 0)

    matched: dict[str, list[str]] = {}
    total_hits = 0

    for category, keywords in keyword_categories.items():
        hits = []
        for kw in keywords:
            pattern = r'\b' + re.escape(kw.lower()) + r'\b'
            if re.search(pattern, text.lower()):
                hits.append(kw)
        if hits:
            matched[category] = hits
            total_hits += len(hits)

    return (matched, total_hits)


def classify_record(
    text: str,
    keyword_categories: dict[str, list[str]],
    cloud_mention_triggers: list[str],
) -> dict:
    """
    Run full intelligence classification on a message.
    Returns a dict ready to populate IntelligenceClassification.
    """
    is_instruction, instruction_text = detect_cloud_mention(text, cloud_mention_triggers)
    matched_keywords, keyword_hits = detect_keywords(text, keyword_categories)
    matched_categories = list(matched_keywords.keys())

    record_type = "instruction" if is_instruction else "observation"

    if is_instruction:
        logger.info("Cloud instruction detected: %s", instruction_text)

    return {
        "record_type": record_type,
        "is_cloud_instruction": is_instruction,
        "instruction_text": instruction_text,
        "matched_categories": matched_categories,
        "matched_keywords": matched_keywords,
        "keyword_hits": keyword_hits,
        "classified_at": datetime.utcnow(),
    }
