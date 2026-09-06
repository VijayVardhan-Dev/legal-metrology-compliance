"""VLM Extraction Service: semantic extraction of packaged-commodity declarations

Communicates with Gemini Vision API using image + OCR text as joint multimodal input.
Produces strictly validated StandardDeclarationExtraction output.
"""
import base64
from io import BytesIO
import json
import logging
from pathlib import Path
import re
from typing import Any, Iterable

import httpx
from PIL import Image

from app.core.config import settings
from app.schemas.declaration_schema import StandardDeclarationExtraction

logger = logging.getLogger(__name__)


class VLMExtractionError(Exception):
    """Raised when VLM extraction fails permanently or encounters an unrecoverable error."""


class VLMExtractorService:
    """Service to call Gemini Vision Flash for semantic declaration extraction."""

    SYSTEM_PROMPT = """You are an information extraction system for Indian packaged-product labels governed by Legal Metrology (Packaged Commodities) Rules and FSSAI regulations.

Analyze the package image together with the supplied OCR results.
Extract legally relevant declarations.
Do not invent information.
Do not infer information that is not visibly supported.
Do not use spatial proximity as the primary method of determining field meaning.
Identify declarations based on semantic meaning.

For every field return:
- value: normalized string value (null if missing)
- evidence: exact supporting evidence text visibly printed on the package / OCR
- confidence: float from 0.0 to 1.0
- status: "found" (clearly visible and legible), "missing" (not visible on package), or "uncertain" (degraded, ambiguous, or incomplete)
- unit: standard unit of measurement if applicable (e.g. "g", "kg", "ml", "l", "INR"), or null

Required JSON output fields:
- product_name
- brand
- net_quantity
- mrp
- manufacturer_name
- manufacturer_address
- packer_name
- packer_address
- importer_name
- importer_address
- date_of_manufacture
- date_of_packing
- best_before
- use_by
- consumer_care_details
- batch_lot_number
- country_of_origin

Return only valid JSON matching this exact structure with no extra conversational text.
"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ):
        self.api_key = api_key if api_key is not None else settings.VLM_API_KEY
        self.model = model or settings.VLM_MODEL or "gemini-3.6-flash"
        self.timeout = timeout or settings.VLM_TIMEOUT_SECONDS or 30

    def is_configured(self) -> bool:
        """Returns True if an API key is present."""
        return bool(self.api_key and self.api_key.strip())

    def _prepare_image_data(
        self,
        image_source: str | Path | bytes | Image.Image,
    ) -> tuple[str, str]:
        """Converts image input into (mime_type, base64_data)."""
        if isinstance(image_source, (str, Path)):
            path = Path(image_source)
            if not path.exists():
                raise VLMExtractionError(f"Image file does not exist: {path.name}")
            ext = path.suffix.lower()
            mime_type = "image/png" if ext == ".png" else "image/webp" if ext == ".webp" else "image/jpeg"
            with open(path, "rb") as f:
                data = f.read()
            return mime_type, base64.b64encode(data).decode("utf-8")

        if isinstance(image_source, bytes):
            return "image/jpeg", base64.b64encode(image_source).decode("utf-8")

        if isinstance(image_source, Image.Image):
            buffer = BytesIO()
            fmt = image_source.format or "JPEG"
            if fmt.upper() not in {"JPEG", "PNG", "WEBP"}:
                fmt = "JPEG"
            image_source.save(buffer, format=fmt)
            mime_type = f"image/{fmt.lower()}"
            return mime_type, base64.b64encode(buffer.getvalue()).decode("utf-8")

        raise VLMExtractionError(f"Unsupported image source type: {type(image_source)}")

    def _format_ocr_context(
        self,
        raw_full_text: str | None,
        regions: Iterable[Any] | None,
    ) -> str:
        """Formats OCR raw text and bounding boxes into clear prompt context."""
        parts = []
        if raw_full_text and raw_full_text.strip():
            parts.append(f"--- OCR FULL RAW TEXT ---\n{raw_full_text.strip()}\n")

        region_list = list(regions or [])
        if region_list:
            parts.append("--- OCR DETECTED REGIONS WITH BOUNDING BOXES & CONFIDENCE ---")
            for idx, r in enumerate(region_list):
                text = str(getattr(r, "text", "") or "").strip()
                if not text:
                    continue
                conf = getattr(r, "confidence", 0.0)
                box = getattr(r, "bounding_box", None)
                x = getattr(r, "bbox_x", None)
                y = getattr(r, "bbox_y", None)
                w = getattr(r, "bbox_width", None)
                h = getattr(r, "bbox_height", None)
                loc = f"[x:{x}, y:{y}, w:{w}, h:{h}]" if x is not None else str(box)
                parts.append(f"Region {idx} (conf: {conf:.2f}, loc: {loc}): \"{text}\"")

        return "\n".join(parts) if parts else "No OCR text available."

    def extract_declarations(
        self,
        image_source: str | Path | bytes | Image.Image,
        raw_full_text: str | None = None,
        regions: Iterable[Any] | None = None,
    ) -> StandardDeclarationExtraction:
        """Synchronously calls Gemini VLM to semantically extract declarations."""
        if not self.is_configured():
            raise VLMExtractionError("VLM API key is not configured in environment (VLM_API_KEY).")

        mime_type, b64_image = self._prepare_image_data(image_source)
        ocr_context = self._format_ocr_context(raw_full_text, regions)

        user_content = f"{self.SYSTEM_PROMPT}\n\n{ocr_context}\n\nExtract all packaged commodity declarations visible on the label into the required structured JSON schema."

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": user_content},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_image,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        logger.info("VLM extraction started with model '%s'", self.model)

        # Attempt call with 1 retry for transient errors or malformed json
        max_attempts = 2
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(url, json=payload)

                if response.status_code != 200:
                    status = response.status_code
                    # Do not log raw response body if it could contain sensitive info
                    logger.warning(
                        "VLM API returned status %d on attempt %d/%d",
                        status,
                        attempt,
                        max_attempts,
                    )
                    if status in {400, 401, 403}:
                        # Auth or client error: no need to retry
                        raise VLMExtractionError(f"VLM API authentication or request error (status {status})")
                    if attempt < max_attempts:
                        continue
                    raise VLMExtractionError(f"VLM API request failed with status {status}")

                data = response.json()
                raw_json = self._parse_candidates(data)
                result = self._validate_and_parse(raw_json)

                found_count = sum(
                    1
                    for _, field in result.model_dump().items()
                    if field.get("status") == "found"
                )
                logger.info(
                    "VLM extraction completed successfully: %d declarations found",
                    found_count,
                )
                return result

            except httpx.TimeoutException as exc:
                logger.warning("VLM API timeout on attempt %d/%d", attempt, max_attempts)
                last_error = VLMExtractionError("VLM API request timed out")
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning("VLM returned malformed JSON on attempt %d/%d: %s", attempt, max_attempts, exc)
                last_error = VLMExtractionError(f"VLM returned invalid JSON: {exc}")
            except VLMExtractionError:
                raise
            except Exception as exc:
                logger.warning("Unexpected error during VLM call on attempt %d/%d: %s", attempt, max_attempts, exc)
                last_error = VLMExtractionError(f"VLM extraction call failed: {exc}")

        raise last_error or VLMExtractionError("VLM extraction failed after retries")

    def _parse_candidates(self, data: dict[str, Any]) -> str:
        """Extracts the text response from Gemini API payload."""
        candidates = data.get("candidates") or []
        if not candidates:
            raise VLMExtractionError("VLM returned empty candidates")

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise VLMExtractionError("VLM candidate has no content parts")

        text = parts[0].get("text", "")
        return text

    def _validate_and_parse(self, text: str) -> StandardDeclarationExtraction:
        """Parses JSON string and validates with StandardDeclarationExtraction."""
        cleaned = text.strip()
        # Strip markdown fences if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        # Attempt to isolate JSON object if extra text surrounds it
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start : end + 1]

        data = json.loads(cleaned)
        if not isinstance(data, dict):
            raise ValueError("VLM response did not parse into a dictionary")

        return StandardDeclarationExtraction.model_validate(data)
