import re
from dataclasses import dataclass
from typing import Any, Iterable

from ai.declaration.normalizer import (
    compact_text,
    normalize_numeric,
    normalize_unit,
    normalize_value,
)
from ai.declaration.patterns import (
    BATCH_PATTERN,
    DATE_PATTERN,
    DECLARATION_TYPES,
    LABEL_PATTERNS,
    MRP_PATTERN,
    QUANTITY_PATTERN,
    RELATIVE_DATE_PATTERN,
    STANDALONE_QUANTITY_PATTERN,
)


@dataclass
class ExtractedDeclaration:
    declaration_type: str
    value: str | None
    normalized_value: Any = None
    unit: str | None = None
    source_text: str = ""
    confidence: float | None = None
    ocr_confidence: float | None = None
    extraction_method: str = "PATTERN"
    status: str = "FOUND"
    ocr_text_region_id: str | None = None


class DeclarationExtractor:
    """Deterministic extraction of declarations from OCR text regions."""

    def extract(self, ocr_result: Any) -> list[ExtractedDeclaration]:
        regions = list(getattr(ocr_result, "text_regions", None) or [])
        return self.extract_regions(regions, getattr(ocr_result, "raw_full_text", None))

    def extract_regions(
        self, regions: Iterable[Any], raw_full_text: str | None = None
    ) -> list[ExtractedDeclaration]:
        region_list = list(regions)
        declarations: list[ExtractedDeclaration] = []
        consumed_ids: set[str] = set()

        for index, region in enumerate(region_list):
            text = str(getattr(region, "text", "") or "")
            if not text.strip():
                continue
            confidence = getattr(region, "confidence", None)
            region_id = getattr(region, "id", None)
            following = self._following_text(region_list, index)

            declaration = self._extract_mrp(text, following, confidence, region_id)
            if declaration:
                declarations.append(declaration)
                consumed_ids.add(region_id)
                continue

            declaration = self._extract_quantity(text, confidence, region_id)
            if declaration:
                declarations.append(declaration)
                consumed_ids.add(region_id)
                continue

            declaration = self._extract_batch(text, confidence, region_id)
            if declaration:
                declarations.append(declaration)
                consumed_ids.add(region_id)
                continue

            date_declarations = self._extract_dates(
                text, following, confidence, region_id
            )
            if date_declarations:
                declarations.extend(date_declarations)
                consumed_ids.add(region_id)
                continue

            for declaration_type, label_pattern in LABEL_PATTERNS.items():
                if not label_pattern.search(text):
                    continue
                declaration = self._extract_labelled(
                    declaration_type,
                    text,
                    following,
                    confidence,
                    region_id,
                )
                if (
                    declaration_type == "CONSUMER_CARE"
                    and declaration.value is None
                ):
                    continue
                declarations.append(declaration)
                consumed_ids.add(region_id)
                break

        quantities = [
            declaration
            for declaration in declarations
            if declaration.declaration_type == "NET_QUANTITY"
        ]
        declarations.extend(
            self._extract_product_name(
                region_list, consumed_ids, quantities, raw_full_text
            )
        )
        return self._deduplicate(declarations)

    def _extract_mrp(self, text, following, confidence, region_id):
        match = MRP_PATTERN.search(text)
        if not match and re.search(r"(?i)\bm\s*\.?\s*r\s*\.?\s*p|maximum\s+retail", text):
            match = None
            source = text
            value = None
            status = "INCOMPLETE"
        elif not match:
            return None
        else:
            source = text
            value = match.group(1).replace(",", "")
            status = "FOUND"

        if value is None and following:
            nearby = re.search(r"(?:₹|rs\.?|inr)?\s*([0-9]+(?:[.,][0-9]{1,2})?)", following, re.I)
            if nearby:
                value = nearby.group(1).replace(",", "")
                source = f"{text} {following}".strip()
                status = "FOUND"
        return ExtractedDeclaration(
            declaration_type="MRP",
            value=value,
            normalized_value=normalize_numeric(value),
            unit="INR" if value is not None else None,
            source_text=source,
            confidence=confidence,
            ocr_confidence=confidence,
            extraction_method="REGEX" if value is not None else "REVIEW_REQUIRED",
            status=status,
            ocr_text_region_id=region_id,
        )

    def _extract_quantity(self, text, confidence, region_id):
        match = QUANTITY_PATTERN.search(text)
        if not match:
            standalone = STANDALONE_QUANTITY_PATTERN.search(text)
            if not standalone or not re.match(r"^\s*[0-9]", text):
                return None
            match = standalone
        if not match:
            return None
        value, unit = match.groups()
        return ExtractedDeclaration(
            declaration_type="NET_QUANTITY",
            value=value.replace(",", ""),
            normalized_value=normalize_numeric(value),
            unit=normalize_unit(unit),
            source_text=text,
            confidence=confidence,
            ocr_confidence=confidence,
            extraction_method="REGEX",
            ocr_text_region_id=region_id,
        )

    def _extract_batch(self, text, confidence, region_id):
        if not re.search(
            r"(?i)\b(?:lot|batch)\b|\bb\s*\.?\s*(?:no|number)\b", text
        ):
            return None
        match = BATCH_PATTERN.search(text)
        value = next((group for group in match.groups() if group), None) if match else None
        return ExtractedDeclaration(
            declaration_type="BATCH_LOT_NUMBER",
            value=value,
            normalized_value=normalize_value(value),
            source_text=text,
            confidence=confidence,
            ocr_confidence=confidence,
            extraction_method="REGEX" if value else "REVIEW_REQUIRED",
            status="FOUND" if value else "INCOMPLETE",
            ocr_text_region_id=region_id,
        )

    def _extract_dates(self, text, following, confidence, region_id):
        compact = compact_text(text)
        if re.search(r"(?i)\b(?:manufactured|mfg|mfd)\s+by\b", text):
            return []
        date_types = []
        if compact.startswith(("mfg", "mfd")):
            date_types.append("MANUFACTURING_DATE")
        if compact.startswith(("pkd", "packed", "packing")) or "pkd" in compact:
            date_types.append("PACKING_DATE")
        if not date_types:
            return []

        value_text = text if not following else f"{text} {following}"
        date_match = DATE_PATTERN.search(text) or DATE_PATTERN.search(following)
        value = date_match.group(0) if date_match else None
        return [
            ExtractedDeclaration(
                declaration_type=date_type,
                value=value,
                normalized_value=normalize_value(value),
                source_text=value_text,
                confidence=confidence,
                ocr_confidence=confidence,
                extraction_method="REGEX" if value else "REVIEW_REQUIRED",
                status="FOUND" if value else "INCOMPLETE",
                ocr_text_region_id=region_id,
            )
            for date_type in date_types
        ]

    def _extract_labelled(self, declaration_type, text, following, confidence, region_id):
        pattern = LABEL_PATTERNS[declaration_type]
        match = pattern.search(text)
        remainder = text[match.end():].strip(" :.-") if match else ""
        combined = remainder
        if not combined and following:
            combined = following
        if declaration_type in {"BEST_BEFORE", "USE_BY"}:
            value_match = RELATIVE_DATE_PATTERN.search(combined) or DATE_PATTERN.search(combined)
            value = value_match.group(0) if value_match else (combined or None)
        elif declaration_type == "CONSUMER_CARE":
            value = self._contact_value(combined or text)
        else:
            value = combined or None
        incomplete = value is None
        return ExtractedDeclaration(
            declaration_type=declaration_type,
            value=value,
            normalized_value=normalize_value(value),
            source_text=text if not following or remainder else f"{text} {following}",
            confidence=confidence,
            ocr_confidence=confidence,
            extraction_method="KEYWORD" if incomplete else "COMBINED",
            status="INCOMPLETE" if incomplete else "FOUND",
            ocr_text_region_id=region_id,
        )

    @staticmethod
    def _contact_value(text: str) -> str | None:
        matches = re.findall(
            r"(?i)(?:\+?\d[\d\s()./-]{7,}\d|[\w.+-]+@[\w.-]+\.[a-z]{2,})",
            text,
        )
        return " / ".join(match.strip() for match in matches) or None

    @staticmethod
    def _following_text(regions, index) -> str:
        if index + 1 >= len(regions):
            return ""
        next_text = str(getattr(regions[index + 1], "text", "") or "").strip()
        if next_text and not any(pattern.search(next_text) for pattern in LABEL_PATTERNS.values()):
            return next_text
        return ""

    @staticmethod
    def _extract_product_name(regions, consumed_ids, quantities, raw_full_text):
        for region in regions:
            region_id = getattr(region, "id", None)
            text = str(getattr(region, "text", "") or "").strip()
            if not text or region_id in consumed_ids:
                continue
            source_text = text
            if (
                MRP_PATTERN.search(text)
                or QUANTITY_PATTERN.search(text)
                or BATCH_PATTERN.search(text)
                or any(pattern.search(text) for pattern in LABEL_PATTERNS.values())
            ):
                continue
            if quantities:
                text = re.sub(
                    r"(?i)\s*[0-9]+(?:[.,][0-9]+)?\s*"
                    r"(?:kg|kgs|g|gm|gram|grams|ml|millilitre|milliliter|"
                    r"l|lt|ltr|litre|liter)\s*$",
                    "",
                    text,
                ).strip()
            if not text:
                continue
            return [
                ExtractedDeclaration(
                    declaration_type="PRODUCT_NAME",
                    value=text,
                    normalized_value=compact_text(text),
                    source_text=source_text,
                    confidence=getattr(region, "confidence", None),
                    ocr_confidence=getattr(region, "confidence", None),
                    extraction_method="PATTERN",
                    ocr_text_region_id=region_id,
                )
            ]
        return []

    @staticmethod
    def _deduplicate(declarations):
        unique = []
        seen = set()
        for declaration in declarations:
            key = (
                declaration.declaration_type,
                declaration.source_text,
                declaration.value,
            )
            if key not in seen:
                seen.add(key)
                unique.append(declaration)
        return unique
