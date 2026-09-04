import logging
from typing import List, Any, Tuple

import numpy as np

from app.schemas.ocr import OCRTextRegionCreate

logger = logging.getLogger(__name__)


def _polygon_to_bbox(poly) -> dict:
    """
    Convert a polygon (Nx2 numpy array or list of [x,y] pairs) to an
    axis-aligned bounding box ``{x, y, width, height}``.
    """
    try:
        if isinstance(poly, np.ndarray):
            xs = poly[:, 0]
            ys = poly[:, 1]
        else:
            xs = [pt[0] for pt in poly]
            ys = [pt[1] for pt in poly]
        x = int(round(min(xs)))
        y = int(round(min(ys)))
        width = int(round(max(xs))) - x
        height = int(round(max(ys))) - y
        return {
            "x": max(0, x),
            "y": max(0, y),
            "width": max(0, width),
            "height": max(0, height),
        }
    except Exception as e:
        logger.warning(f"Error computing bbox from polygon {poly}: {e}")
        return {"x": 0, "y": 0, "width": 0, "height": 0}


def _poly_to_list(poly) -> list:
    """Convert a numpy polygon array to a JSON-serialisable list of [x, y]."""
    if isinstance(poly, np.ndarray):
        return poly.tolist()
    if isinstance(poly, (list, tuple)):
        return [
            pt.tolist()
            if isinstance(pt, np.ndarray)
            else list(pt)
            if isinstance(pt, (list, tuple))
            else pt
            for pt in poly
        ]
    return poly


def _is_line_item(x: Any) -> bool:
    """Checks if x is in PaddleOCR v2 style: [poly, (text, conf)]."""
    return (
        isinstance(x, (list, tuple))
        and len(x) == 2
        and isinstance(x[1], (list, tuple))
        and len(x[1]) >= 2
    )


def parse_ocr_results(
    raw_result: Any, ocr_result_id: str
) -> Tuple[List[OCRTextRegionCreate], str, float]:
    """
    Parse PaddleOCR **v3.x** and **v2.x** output into structured
    ``OCRTextRegionCreate`` instances.

    Supports:
      - PaddleOCR 3.x ``OCRResult`` (dict-like with rec_texts, rec_scores, dt_polys)
      - Standard dicts
      - PaddleOCR 2.x nested lists:
          - Single page of line items: `[[poly, (text, score)], ...]`
          - Multiple pages: `[[[poly, (text, score)], ...], ...]`

    Returns
    -------
    (regions, raw_full_text, average_confidence)
    """
    regions: List[OCRTextRegionCreate] = []
    full_text_parts: List[str] = []
    total_confidence = 0.0
    valid_count = 0

    if not raw_result:
        return regions, "", 0.0

    # Normalize raw_result into a list of "pages" or items
    pages = raw_result
    if isinstance(raw_result, (list, tuple)) and len(raw_result) > 0 and _is_line_item(raw_result[0]):
        # raw_result is directly a list of [poly, (text, conf)] line items
        pages = [raw_result]

    for page in pages:
        if page is None:
            continue

        # Format 1: Dict-like (PaddleOCR 3.x OCRResult)
        if hasattr(page, "get"):
            rec_texts = page.get("rec_texts") or []
            rec_scores = page.get("rec_scores") or []
            dt_polys = page.get("dt_polys")
            if dt_polys is None or len(dt_polys) == 0:
                dt_polys = page.get("rec_polys") or []

            for i, text in enumerate(rec_texts):
                conf = float(rec_scores[i]) if i < len(rec_scores) else 0.0
                poly = dt_polys[i] if i < len(dt_polys) else [[0, 0], [0, 0], [0, 0], [0, 0]]
                bbox = _polygon_to_bbox(poly)
                poly_list = _poly_to_list(poly)

                regions.append(
                    OCRTextRegionCreate(
                        ocr_result_id=ocr_result_id,
                        text=str(text),
                        confidence=conf,
                        bounding_box=poly_list,
                        bbox_x=bbox["x"],
                        bbox_y=bbox["y"],
                        bbox_width=bbox["width"],
                        bbox_height=bbox["height"],
                    )
                )
                full_text_parts.append(str(text))
                total_confidence += conf
                valid_count += 1

        # Format 2: Object with attributes
        elif hasattr(page, "rec_texts"):
            rec_texts = getattr(page, "rec_texts", None) or []
            rec_scores = getattr(page, "rec_scores", None) or []
            dt_polys = getattr(page, "dt_polys", None)
            if dt_polys is None or len(dt_polys) == 0:
                dt_polys = getattr(page, "rec_polys", None) or []

            for i, text in enumerate(rec_texts):
                conf = float(rec_scores[i]) if i < len(rec_scores) else 0.0
                poly = dt_polys[i] if i < len(dt_polys) else [[0, 0], [0, 0], [0, 0], [0, 0]]
                bbox = _polygon_to_bbox(poly)
                poly_list = _poly_to_list(poly)

                regions.append(
                    OCRTextRegionCreate(
                        ocr_result_id=ocr_result_id,
                        text=str(text),
                        confidence=conf,
                        bounding_box=poly_list,
                        bbox_x=bbox["x"],
                        bbox_y=bbox["y"],
                        bbox_width=bbox["width"],
                        bbox_height=bbox["height"],
                    )
                )
                full_text_parts.append(str(text))
                total_confidence += conf
                valid_count += 1

        # Format 3: PaddleOCR 2.x list of line items
        elif isinstance(page, (list, tuple)):
            for item in page:
                if _is_line_item(item):
                    poly = item[0]
                    text = str(item[1][0])
                    conf = float(item[1][1])

                    bbox = _polygon_to_bbox(poly)
                    poly_list = _poly_to_list(poly)

                    regions.append(
                        OCRTextRegionCreate(
                            ocr_result_id=ocr_result_id,
                            text=text,
                            confidence=conf,
                            bounding_box=poly_list,
                            bbox_x=bbox["x"],
                            bbox_y=bbox["y"],
                            bbox_width=bbox["width"],
                            bbox_height=bbox["height"],
                        )
                    )
                    full_text_parts.append(text)
                    total_confidence += conf
                    valid_count += 1

    raw_full_text = "\n".join(full_text_parts)
    average_confidence = (total_confidence / valid_count) if valid_count > 0 else 0.0

    return regions, raw_full_text, average_confidence
