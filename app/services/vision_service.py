from __future__ import annotations

import logging
from typing import Optional

from google.cloud import vision

logger = logging.getLogger(__name__)

_client: Optional[vision.ImageAnnotatorClient] = None

OCR_TEXT_MAX_CHARS = 50_000  # Truncate before storing in Firestore


def _get_client() -> vision.ImageAnnotatorClient:
    global _client
    if _client is None:
        _client = vision.ImageAnnotatorClient()
    return _client


def ocr_from_gcs_uri(gcs_uri: str) -> tuple[str, float]:
    """
    Run document text detection on an image already in GCS.
    Returns (extracted_text, mean_confidence). Prefers this over
    ocr_from_bytes to avoid re-downloading the image.
    """
    client = _get_client()
    image = vision.Image(source=vision.ImageSource(gcs_image_uri=gcs_uri))
    response = client.document_text_detection(image=image)

    if response.error.message:
        logger.error("Vision API error for %s: %s", gcs_uri, response.error.message)
        return ("", 0.0)

    full_text = ""
    confidence = 0.0

    if response.full_text_annotation:
        full_text = response.full_text_annotation.text or ""
        pages = response.full_text_annotation.pages
        if pages:
            confidences = [
                word.confidence
                for page in pages
                for block in page.blocks
                for para in block.paragraphs
                for word in para.words
                if word.confidence > 0
            ]
            confidence = sum(confidences) / len(confidences) if confidences else 0.0

    if len(full_text) > OCR_TEXT_MAX_CHARS:
        full_text = full_text[:OCR_TEXT_MAX_CHARS]

    logger.info("OCR complete for %s — %d chars, confidence %.2f", gcs_uri, len(full_text), confidence)
    return (full_text, confidence)


def ocr_from_bytes(image_bytes: bytes, content_type: str = "image/png") -> tuple[str, float]:
    """
    Run document text detection on raw image bytes.
    Use ocr_from_gcs_uri when possible to avoid re-downloading.
    """
    client = _get_client()
    image = vision.Image(content=image_bytes)
    response = client.document_text_detection(image=image)

    if response.error.message:
        logger.error("Vision API error: %s", response.error.message)
        return ("", 0.0)

    full_text = ""
    confidence = 0.0

    if response.full_text_annotation:
        full_text = response.full_text_annotation.text or ""
        pages = response.full_text_annotation.pages
        if pages:
            confidences = [
                word.confidence
                for page in pages
                for block in page.blocks
                for para in block.paragraphs
                for word in para.words
                if word.confidence > 0
            ]
            confidence = sum(confidences) / len(confidences) if confidences else 0.0

    if len(full_text) > OCR_TEXT_MAX_CHARS:
        full_text = full_text[:OCR_TEXT_MAX_CHARS]

    logger.info("OCR complete — %d chars, confidence %.2f", len(full_text), confidence)
    return (full_text, confidence)
