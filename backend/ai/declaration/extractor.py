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
    ocr_text_region_ids: list[str] | None = None


class DeclarationExtractor:
    """Deterministic extraction of declarations from OCR text regions."""

    def extract(self, ocr_result: Any) -> list[ExtractedDeclaration]:
        regions = list(getattr(ocr_result, "text_regions", None) or [])
        return self.extract_regions(regions, getattr(ocr_result, "raw_full_text", None))

    def extract_regions(
        self,
        regions: Iterable[Any],
        raw_full_text: str | None = None,
        proximity_threshold: int = 180,
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

            combined = self._extract_spatial_labelled(
                region_list, index, proximity_threshold, consumed_ids
            )
            if combined:
                declaration, ids = combined
                declarations.append(declaration)
                consumed_ids.update(ids)
                continue

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
        declarations.extend(self._extract_spatial_consumer_care(region_list, consumed_ids))
        return self._remove_redundant_incomplete(self._deduplicate(declarations))

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

    def _extract_spatial_labelled(self, regions, index, threshold, consumed_ids):
        if not self._has_geometry(regions[index]):
            return None
        text = str(getattr(regions[index], "text", "") or "").strip()
        compact = compact_text(text)
        if compact in {"mrp", "maximumretailprice"}:
            return self._spatial_mrp(regions, index, threshold)
        if compact in {"batch", "lot", "bno"} or compact.startswith(("batch", "lot")):
            return self._spatial_batch(regions, index, threshold, consumed_ids)
        if compact in {"manufactured", "manufacturing"}:
            return self._spatial_manufacturer(regions, index, threshold)
        if compact in {"mfg", "mfd"}:
            return self._spatial_date(regions, index, threshold, "MANUFACTURING_DATE")
        if compact in {"best", "bestbefore"}:
            return self._spatial_date(regions, index, threshold, "BEST_BEFORE")
        if compact in {"use", "useby", "expiry", "expirydate", "exp", "expdate"}:
            return self._spatial_date(regions, index, threshold, "USE_BY")
        if compact in {"net", "netwt", "netweight"} or (
            compact.startswith("net") and any(token in compact for token in ("wt", "weight", "qty", "quantity"))
        ):
            return self._spatial_quantity(regions, index, threshold)
        if compact in {"product", "of"}:
            return self._spatial_country(regions, index, threshold)
        if compact in {"phone", "email", "contact", "consumercare", "customercare"}:
            return self._spatial_consumer_care(regions, index, threshold)
        return None

    def _spatial_mrp(self, regions, index, threshold):
        candidates = self._nearby(regions, index, threshold)
        value = next(
            (item for item in candidates if re.fullmatch(r"\d+(?:[.,]\d{1,2})?", str(getattr(item, "text", "")).strip())),
            None,
        )
        if not value:
            return self._make_incomplete("MRP", regions[index])
        source, items = self._source_and_items(regions, index, [value])
        declaration = ExtractedDeclaration(
            declaration_type="MRP",
            value=str(getattr(value, "text", "")).strip(),
            normalized_value=str(getattr(value, "text", "")).strip().replace(",", ""),
            unit="INR",
            source_text=source,
            confidence=self._combined_confidence(items),
            ocr_confidence=self._combined_confidence(items),
            extraction_method="COMBINED",
            ocr_text_region_id=self._region_id(regions[index]),
            ocr_text_region_ids=[self._region_id(item) for item in items],
        )
        return declaration, {self._region_id(item) for item in items}

    def _spatial_batch(self, regions, index, threshold, consumed_ids):
        candidates = [
            item for item in self._nearby(regions, index, threshold)
            if self._region_id(item) not in consumed_ids
        ]
        same_line = [item for item in candidates if self._same_line(regions[index], item)]
        candidates = same_line or [
            item for item in candidates
            if self._vertical_gap(regions[index], item) <= max(self._bbox(regions[index])[3], 20)
        ]
        value = next(
            (item for item in candidates if re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9./_-]*", str(getattr(item, "text", "")).strip()
            ) and compact_text(str(getattr(item, "text", ""))) not in {"no", "number"}
             and not self._is_label_text(str(getattr(item, "text", "")))),
            None,
        )
        if not value:
            return self._make_incomplete("BATCH_LOT_NUMBER", regions[index])
        source, items = self._source_and_items(regions, index, [value])
        declaration = ExtractedDeclaration(
            declaration_type="BATCH_LOT_NUMBER",
            value=str(getattr(value, "text", "")).strip(),
            normalized_value=normalize_value(str(getattr(value, "text", "")).strip()),
            source_text=source,
            confidence=self._combined_confidence(items),
            ocr_confidence=self._combined_confidence(items),
            extraction_method="COMBINED",
            ocr_text_region_id=self._region_id(regions[index]),
            ocr_text_region_ids=[self._region_id(item) for item in items],
        )
        return declaration, {self._region_id(item) for item in items}

    def _spatial_date(self, regions, index, threshold, declaration_type):
        candidates = [
            item for item in regions
            if item is not regions[index] and self._same_line(regions[index], item)
        ]
        if not candidates:
            candidates = self._nearby(regions, index, threshold)
        compact_date = next(
            (item for item in candidates if DATE_PATTERN.fullmatch(
                re.sub(r"[^A-Za-z0-9./-]", "", str(getattr(item, "text", "")))
            )),
            None,
        )
        if compact_date:
            source, items = self._source_and_items(regions, index, [compact_date])
            value = str(getattr(compact_date, "text", "")).strip().upper()
            return ExtractedDeclaration(
                declaration_type=declaration_type,
                value=value,
                normalized_value=value,
                source_text=source,
                confidence=self._combined_confidence(items),
                ocr_confidence=self._combined_confidence(items),
                extraction_method="COMBINED",
                ocr_text_region_id=self._region_id(regions[index]),
                ocr_text_region_ids=[self._region_id(item) for item in items],
            ), {self._region_id(item) for item in items}
        numbers = [item for item in candidates if re.fullmatch(r"\d{1,4}", str(getattr(item, "text", "")).strip())]
        month = next(
            (item for item in candidates if compact_text(str(getattr(item, "text", "")))[:3] in
             {"jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"}),
            None,
        )
        day = next((item for item in numbers if len(str(getattr(item, "text", "")).strip()) <= 2), None)
        year = next((item for item in numbers if len(str(getattr(item, "text", "")).strip()) == 4), None)
        if not month or not day or not year:
            # Let the normal labelled-text extractor try the complete OCR line
            # before reporting an incomplete declaration.
            return None
        label_items = [
            item for item in candidates
            if compact_text(str(getattr(item, "text", ""))) in {
                "best", "before", "bestbefore", "use", "by", "useby",
                "expiry", "expirydate", "exp", "expdate", "date",
            }
            and self._same_line(regions[index], item)
        ]
        source, items = self._source_and_items(
            regions, index, label_items + [day, month, year]
        )
        value = " ".join(
            [str(getattr(day, "text", "")).strip(),
             str(getattr(month, "text", "")).strip().upper(),
             str(getattr(year, "text", "")).strip()]
        )
        declaration = ExtractedDeclaration(
            declaration_type=declaration_type,
            value=value,
            normalized_value=value,
            source_text=source,
            confidence=self._combined_confidence(items),
            ocr_confidence=self._combined_confidence(items),
            extraction_method="COMBINED",
            ocr_text_region_id=self._region_id(regions[index]),
            ocr_text_region_ids=[self._region_id(item) for item in items],
        )
        return declaration, {self._region_id(item) for item in items}

    def _spatial_quantity(self, regions, index, threshold):
        candidates = self._nearby(regions, index, threshold)
        same_line = [item for item in candidates if self._same_line(regions[index], item)]
        candidates = same_line or [
            item for item in candidates
            if self._vertical_gap(regions[index], item) <= max(self._bbox(regions[index])[3], 20)
        ]
        number = next((item for item in candidates if re.fullmatch(
            r"\d+(?:[.,]\d+)?", str(getattr(item, "text", "")).strip()
        )), None)
        if not number:
            return self._make_incomplete("NET_QUANTITY", regions[index])
        number_index = regions.index(number)
        number_x, number_y, number_w, number_h = self._bbox(number)
        unit_candidates = [
            item for item in candidates
            if normalize_unit(str(getattr(item, "text", "")).strip())
            in {"g", "kg", "ml", "L"}
            and self._unit_is_adjacent_to_number(
                number, item, threshold, regions.index(item), number_index
            )
        ]
        unit = min(
            unit_candidates,
            key=lambda item: self._distance(number, item),
            default=None,
        )
        label_items = [
            item for item in candidates
            if compact_text(str(getattr(item, "text", ""))) in {
                "wt", "weight", "quantity", "qty"
            }
            and regions.index(item) < number_index
        ]
        items = label_items + [number] + ([unit] if unit else [])
        source, selected = self._source_and_items(regions, index, items)
        declaration = ExtractedDeclaration(
            declaration_type="NET_QUANTITY",
            value=str(getattr(number, "text", "")).strip(),
            normalized_value=normalize_numeric(str(getattr(number, "text", "")).strip()),
            unit=normalize_unit(str(getattr(unit, "text", "")).strip()) if unit else None,
            source_text=source,
            confidence=self._combined_confidence(selected),
            ocr_confidence=self._combined_confidence(selected),
            extraction_method="COMBINED",
            ocr_text_region_id=self._region_id(regions[index]),
            ocr_text_region_ids=[self._region_id(item) for item in selected],
        )
        return declaration, {self._region_id(item) for item in selected}

    def _unit_is_adjacent_to_number(
        self, number, unit, threshold, unit_index, number_index
    ):
        nx, ny, nw, nh = self._bbox(number)
        ux, uy, uw, uh = self._bbox(unit)
        if not any((nw, nh, uw, uh)):
            return True
        same_line = abs((uy + uh / 2) - (ny + nh / 2)) <= max(nh, uh, 20)
        right_of_number = ux >= nx + nw and ux - (nx + nw) <= threshold
        below_number = uy >= ny + nh and uy - (ny + nh) <= threshold and abs(ux - nx) <= threshold
        return (same_line and right_of_number) or below_number

    def _same_line(self, first, second):
        _, ay, _, ah = self._bbox(first)
        _, by, _, bh = self._bbox(second)
        return abs((by + bh / 2) - (ay + ah / 2)) <= max(ah, bh, 20)

    def _vertical_gap(self, first, second):
        _, ay, _, ah = self._bbox(first)
        _, by, _, _ = self._bbox(second)
        return max(0, by - (ay + ah))

    def _spatial_manufacturer(self, regions, index, threshold):
        candidates = self._nearby(regions, index, threshold)
        useful = [
            item for item in candidates
            if compact_text(str(getattr(item, "text", ""))) not in {"by", "manufactured", "manufacturing"}
            and not self._is_label_text(str(getattr(item, "text", "")))
        ]
        if not useful:
            return self._make_incomplete("MANUFACTURER", regions[index])
        source, selected = self._source_and_items(
            regions, index, useful
        )
        value_parts = []
        started = False
        noise = {
            "store", "in", "a", "cool,", "cool", "dry", "place", "away",
            "from", "direct", "sunlight",
        }
        for item in selected:
            item_text = str(getattr(item, "text", "")).strip()
            compact_item = compact_text(item_text)
            if not started and compact_item not in {"ms", "m/s"}:
                continue
            started = True
            if compact_item not in noise:
                value_parts.append(item_text)
        value = " ".join(value_parts).strip()
        if not value:
            return self._make_incomplete("MANUFACTURER", regions[index])
        declaration = ExtractedDeclaration(
            declaration_type="MANUFACTURER",
            value=value,
            normalized_value=normalize_value(value),
            source_text=source,
            confidence=self._combined_confidence(selected),
            ocr_confidence=self._combined_confidence(selected),
            extraction_method="COMBINED",
            ocr_text_region_id=self._region_id(regions[index]),
            ocr_text_region_ids=[self._region_id(item) for item in selected],
        )
        return declaration, {self._region_id(item) for item in selected}

    def _spatial_country(self, regions, index, threshold):
        if compact_text(str(getattr(regions[index], "text", ""))) != "product":
            return None
        candidates = self._nearby(regions, index, threshold)
        india = next((item for item in candidates if compact_text(str(getattr(item, "text", ""))) == "india"), None)
        if not india:
            return None
        source, selected = self._source_and_items(regions, index, [india])
        declaration = ExtractedDeclaration(
            declaration_type="COUNTRY_OF_ORIGIN",
            value="INDIA",
            normalized_value="INDIA",
            source_text=source,
            confidence=self._combined_confidence(selected),
            ocr_confidence=self._combined_confidence(selected),
            extraction_method="COMBINED",
            ocr_text_region_id=self._region_id(regions[index]),
            ocr_text_region_ids=[self._region_id(item) for item in selected],
        )
        return declaration, {self._region_id(item) for item in selected}

    def _nearby(self, regions, index, threshold):
        anchor = regions[index]
        ax, ay, aw, ah = self._bbox(anchor)
        results = []
        for candidate_index, candidate in enumerate(regions):
            if candidate_index == index:
                continue
            bx, by, bw, bh = self._bbox(candidate)
            horizontal = bx >= ax + aw and bx - (ax + aw) <= threshold and abs(by - ay) <= threshold
            vertical = by >= ay + ah and by - (ay + ah) <= threshold and abs(bx - ax) <= threshold
            if horizontal or vertical or not (aw or ah or bw or bh):
                same_line = abs((by + bh / 2) - (ay + ah / 2)) <= max(ah, bh, 20)
                results.append(
                    (
                        0 if same_line else 1,
                        self._distance(anchor, candidate),
                        str(getattr(candidate, "text", "")).strip(),
                        candidate,
                    )
                )
        return [item for _, _, _, item in sorted(results, key=lambda item: (item[0], item[1]))]

    @staticmethod
    def _bbox(region):
        return (
            getattr(region, "bbox_x", None) or 0,
            getattr(region, "bbox_y", None) or 0,
            getattr(region, "bbox_width", None) or 0,
            getattr(region, "bbox_height", None) or 0,
        )

    @classmethod
    def _has_geometry(cls, region):
        return any(
            getattr(region, field, None) is not None
            for field in ("bbox_x", "bbox_y", "bbox_width", "bbox_height")
        )

    @classmethod
    def _distance(cls, first, second):
        ax, ay, aw, ah = cls._bbox(first)
        bx, by, bw, bh = cls._bbox(second)
        return abs((ax + aw / 2) - (bx + bw / 2)) + abs((ay + ah / 2) - (by + bh / 2))

    @staticmethod
    def _region_id(region):
        return getattr(region, "id", None)

    @staticmethod
    def _combined_confidence(regions):
        values = [getattr(region, "confidence", None) for region in regions]
        values = [value for value in values if value is not None]
        return min(values) if values else None

    @staticmethod
    def _source_and_items(regions, index, ids):
        selected = [regions[index]]
        selected.extend(region for region in regions if region in ids)
        return " ".join(str(getattr(item, "text", "")).strip() for item in selected), selected

    @staticmethod
    def _is_label_text(text):
        compact = compact_text(text)
        return compact in {
            "mrp", "batch", "no", "number", "mfg", "date", "best", "before",
            "net", "wt", "phone", "email", "product", "of", "india",
        }

    @staticmethod
    def _make_incomplete(declaration_type, region):
        return (
            ExtractedDeclaration(
                declaration_type=declaration_type,
                value=None,
                source_text=str(getattr(region, "text", "") or "").strip(),
                confidence=getattr(region, "confidence", None),
                ocr_confidence=getattr(region, "confidence", None),
                extraction_method="REVIEW_REQUIRED",
                status="INCOMPLETE",
                ocr_text_region_id=getattr(region, "id", None),
                ocr_text_region_ids=[getattr(region, "id", None)],
            ),
            {getattr(region, "id", None)},
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
            compact_combined = compact_text(combined)
            compact_relative = re.search(
                r"\d+(?:months?|years?|days?)fromthedateofpacking",
                compact_combined,
                re.IGNORECASE,
            )
            relative_period = (
                declaration_type == "BEST_BEFORE"
                and re.search(r"\b\d+\s+(?:months?|years?|days?)\b", combined, re.IGNORECASE)
            )
            value = (
                value_match.group(0)
                if value_match
                else combined.strip(" \"'") if compact_relative or relative_period
                else None
            )
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
        normalized = []
        for match in matches:
            value = match.strip()
            # PaddleOCR can drop the leading "i" in a clearly labelled email.
            if value.lower().startswith("nfo@"):
                value = "i" + value
            normalized.append(value)
        return " / ".join(normalized) or None

    @staticmethod
    def _following_text(regions, index) -> str:
        if index + 1 >= len(regions):
            return ""
        next_text = str(getattr(regions[index + 1], "text", "") or "").strip()
        if next_text and not any(pattern.search(next_text) for pattern in LABEL_PATTERNS.values()):
            return next_text
        return ""

    def _extract_product_name(self, regions, consumed_ids, quantities, raw_full_text):
        for index, region in enumerate(regions):
            if not self._has_geometry(region) or self._region_id(region) in consumed_ids:
                continue
            text = str(getattr(region, "text", "") or "").strip()
            if not text or self._is_label_text(text):
                continue
            group = [region]
            ax, ay, aw, ah = self._bbox(region)
            for candidate in regions[index + 1:]:
                if self._region_id(candidate) in consumed_ids:
                    continue
                candidate_text = str(getattr(candidate, "text", "") or "").strip()
                bx, by, bw, bh = self._bbox(candidate)
                if self._is_label_text(candidate_text) or re.search(r"\d", candidate_text):
                    break
                if bx >= ax + aw and bx - (ax + aw) <= 120 and abs(
                    (by + bh / 2) - (ay + ah / 2)
                ) <= max(ah, bh, 12) / 2:
                    group.append(candidate)
                else:
                    break
            if len(group) > 1:
                source_text = " ".join(str(getattr(item, "text", "")).strip() for item in group)
                value = re.split(r"(?i)\bstore\s+in\b", source_text, maxsplit=1)[0].strip()
                if not value:
                    continue
                confidence = DeclarationExtractor._combined_confidence(group)
                return [
                    ExtractedDeclaration(
                        declaration_type="PRODUCT_NAME",
                        value=value,
                        normalized_value=compact_text(value),
                        source_text=source_text,
                        confidence=confidence,
                        ocr_confidence=confidence,
                        extraction_method="COMBINED",
                        ocr_text_region_id=self._region_id(region),
                        ocr_text_region_ids=[self._region_id(item) for item in group],
                    )
                ]
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
    def _remove_redundant_incomplete(declarations):
        found_types = {
            declaration.declaration_type
            for declaration in declarations
            if declaration.status == "FOUND" and declaration.value
        }
        return [
            declaration
            for declaration in declarations
            if not (
                declaration.status == "INCOMPLETE"
                and declaration.declaration_type in found_types
            )
        ]

    def _spatial_consumer_care(self, regions, index, threshold):
        candidates = self._nearby(regions, index, threshold)
        contacts = [
            item for item in candidates
            if re.search(r"(?i)(?:\+?\d[\d\s()./-]{7,}\d|[\w.+-]+@[\w.-]+\.[a-z]{2,})",
                         str(getattr(item, "text", "")))
        ]
        if not contacts:
            return None
        source, selected = self._source_and_items(regions, index, contacts)
        value = self._contact_value(" ".join(str(getattr(item, "text", "")) for item in selected))
        declaration = ExtractedDeclaration(
            declaration_type="CONSUMER_CARE",
            value=value,
            normalized_value=normalize_value(value),
            source_text=source,
            confidence=self._combined_confidence(selected),
            ocr_confidence=self._combined_confidence(selected),
            extraction_method="COMBINED",
            ocr_text_region_id=self._region_id(regions[index]),
            ocr_text_region_ids=[self._region_id(item) for item in selected],
        )
        return declaration, {self._region_id(item) for item in selected}

    def _extract_spatial_consumer_care(self, regions, consumed_ids):
        for index, region in enumerate(regions):
            if self._region_id(region) in consumed_ids or not self._has_geometry(region):
                continue
            if compact_text(str(getattr(region, "text", ""))) not in {"phone", "email"}:
                continue
            result = self._spatial_consumer_care(regions, index, 180)
            if result:
                declaration, _ = result
                return [declaration]
        return []

    @staticmethod
    def _deduplicate(declarations):
        unique = []
        seen = set()
        best_consumer_care = None
        for declaration in declarations:
            if declaration.declaration_type == "CONSUMER_CARE":
                if best_consumer_care is None or len(declaration.value or "") > len(
                    best_consumer_care.value or ""
                ):
                    best_consumer_care = declaration
                continue
            key = (
                declaration.declaration_type,
                declaration.source_text,
                declaration.value,
            )
            if key not in seen:
                seen.add(key)
                unique.append(declaration)
        if best_consumer_care is not None:
            unique.append(best_consumer_care)
        return unique
