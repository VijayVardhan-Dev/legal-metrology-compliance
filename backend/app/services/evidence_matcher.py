"""Evidence Matcher: associates semantic VLM evidence with OCR text regions.

Normalizes text, applies robust fuzzy matching (RapidFuzz), and resolves bounding boxes.
"""
from dataclasses import dataclass, field
import logging
import re
import unicodedata
from typing import Any, Iterable

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    fuzz = None

logger = logging.getLogger(__name__)


@dataclass
class EvidenceMatchResult:
    matched: bool
    ocr_text_region_id: str | None = None
    ocr_text_region_ids: list[str] = field(default_factory=list)
    ocr_confidence: float | None = None
    bbox: dict[str, int] | None = None
    match_score: float = 0.0
    matched_text: str = ""


class EvidenceMatcher:
    """Matches evidence strings to OCR regions using text normalization and fuzzy scoring."""

    MATCH_THRESHOLD = 55.0  # Minimum fuzzy score (0-100)

    @classmethod
    def normalize_text(cls, text: str | None) -> str:
        if not text:
            return ""
        # 1. Unicode decomposition
        normalized = unicodedata.normalize("NFKD", str(text))
        # 2. Currency normalization: unify ₹, Rs, Rs., INR
        normalized = re.sub(r"(?i)(?:₹|rs\.?|inr)", " inr ", normalized)
        # 3. Units normalization
        normalized = re.sub(r"(?i)\b(?:gm|grams?)\b", "g", normalized)
        normalized = re.sub(r"(?i)\b(?:millilitres?|milliliters?)\b", "ml", normalized)
        normalized = re.sub(r"(?i)\b(?:litres?|liters?)\b", "l", normalized)
        # 4. Standardize punctuation & symbols to space
        normalized = re.sub(r"[^a-zA-Z0-9\s]", " ", normalized)
        # 5. Collapse multiple whitespace and lowercase
        return " ".join(normalized.lower().split())

    def match_evidence(
        self,
        evidence: str | None,
        regions: Iterable[Any],
        raw_full_text: str | None = None,
    ) -> EvidenceMatchResult:
        """Finds the best matching OCR text region(s) for a given evidence text."""
        if not evidence or not evidence.strip():
            return EvidenceMatchResult(matched=False)

        region_list = [r for r in regions if getattr(r, "text", None)]
        if not region_list:
            return EvidenceMatchResult(matched=False)

        norm_evidence = self.normalize_text(evidence)
        if not norm_evidence:
            return EvidenceMatchResult(matched=False)

        best_score = 0.0
        best_regions: list[Any] = []

        # 1. Try single-region exact or fuzzy match
        for region in region_list:
            region_text = getattr(region, "text", "") or ""
            norm_region = self.normalize_text(region_text)
            if not norm_region:
                continue

            # Exact substring bonus
            if norm_evidence in norm_region or norm_region in norm_evidence:
                score = 95.0 + (min(len(norm_region), len(norm_evidence)) / max(len(norm_region), len(norm_evidence), 1) * 5.0)
            elif fuzz:
                token_set = fuzz.token_set_ratio(norm_evidence, norm_region)
                partial = fuzz.partial_ratio(norm_evidence, norm_region)
                score = (token_set * 0.6) + (partial * 0.4)
            else:
                score = 70.0 if (norm_evidence in norm_region or norm_region in norm_evidence) else 0.0

            if score > best_score:
                best_score = score
                best_regions = [region]

        # 2. Multi-region evaluation (sliding windows of 2 to 4 consecutive regions)
        # This handles cases where evidence spans multiple lines (e.g. manufacturer name + address)
        n = len(region_list)
        for window_size in (2, 3, 4):
            if n < window_size:
                continue
            for i in range(n - window_size + 1):
                group = region_list[i : i + window_size]
                combined_text = " ".join(getattr(r, "text", "") or "" for r in group)
                norm_combined = self.normalize_text(combined_text)

                if norm_evidence == norm_combined:
                    score = 100.0
                elif norm_combined in norm_evidence:
                    coverage = len(norm_combined) / max(len(norm_evidence), 1)
                    score = 90.0 + (coverage * 9.9)
                elif norm_evidence in norm_combined:
                    coverage = len(norm_evidence) / max(len(norm_combined), 1)
                    score = 90.0 + (coverage * 9.9)
                elif fuzz:
                    token_set = fuzz.token_set_ratio(norm_evidence, norm_combined)
                    partial = fuzz.partial_ratio(norm_evidence, norm_combined)
                    score = (token_set * 0.65) + (partial * 0.35)
                else:
                    score = 75.0 if norm_evidence in norm_combined else 0.0

                if score > best_score and score >= self.MATCH_THRESHOLD:
                    best_score = score
                    best_regions = group

        if best_score < self.MATCH_THRESHOLD or not best_regions:
            logger.debug(
                "Evidence matching below threshold: evidence='%s', best_score=%.1f",
                evidence,
                best_score,
            )
            return EvidenceMatchResult(matched=False, match_score=best_score)

        # 3. Calculate composite bounding box and average confidence
        valid_boxes = [
            (
                getattr(r, "bbox_x", None),
                getattr(r, "bbox_y", None),
                getattr(r, "bbox_width", None),
                getattr(r, "bbox_height", None),
            )
            for r in best_regions
            if getattr(r, "bbox_x", None) is not None
            and getattr(r, "bbox_y", None) is not None
            and getattr(r, "bbox_width", None) is not None
            and getattr(r, "bbox_height", None) is not None
        ]

        composite_bbox = None
        if valid_boxes:
            min_x = min(x for x, y, w, h in valid_boxes)
            min_y = min(y for x, y, w, h in valid_boxes)
            max_x = max(x + w for x, y, w, h in valid_boxes)
            max_y = max(y + h for x, y, w, h in valid_boxes)
            composite_bbox = {
                "x": int(min_x),
                "y": int(min_y),
                "width": int(max_x - min_x),
                "height": int(max_y - min_y),
            }

        confidences = [
            getattr(r, "confidence", 0.0)
            for r in best_regions
            if getattr(r, "confidence", None) is not None
        ]
        avg_ocr_conf = (
            sum(confidences) / len(confidences) if confidences else None
        )

        matched_ids = [
            str(getattr(r, "id"))
            for r in best_regions
            if getattr(r, "id", None) is not None
        ]
        primary_id = matched_ids[0] if matched_ids else None
        matched_text = " ".join(getattr(r, "text", "") for r in best_regions)

        logger.debug(
            "Matched evidence '%s' to %d region(s) (primary_id=%s, score=%.1f)",
            evidence,
            len(best_regions),
            primary_id,
            best_score,
        )

        return EvidenceMatchResult(
            matched=True,
            ocr_text_region_id=primary_id,
            ocr_text_region_ids=matched_ids,
            ocr_confidence=avg_ocr_conf,
            bbox=composite_bbox,
            match_score=best_score,
            matched_text=matched_text,
        )
