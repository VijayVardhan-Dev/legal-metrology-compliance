import logging
import re
from typing import Any

import cv2

logger = logging.getLogger(__name__)
BARCODE_PATTERN = re.compile(r"\b\d{8,14}\b")


def detect_barcode(image_path: str) -> str | None:
    """Detect the first valid numeric retail barcode using OpenCV's detector."""
    image = cv2.imread(image_path)
    if image is None or not hasattr(cv2, "barcode_BarcodeDetector"):
        return None
    try:
        detector = cv2.barcode_BarcodeDetector()
        result = detector.detectAndDecode(image)
        if isinstance(result, tuple):
            # OpenCV 4.x returns either (decoded, points, straight) or
            # (ok, decoded_info, points, straight) depending on the build.
            decoded = result[1] if len(result) >= 4 and isinstance(result[1], (list, tuple)) else result[0]
        else:
            decoded = result
        values = decoded if isinstance(decoded, (list, tuple)) else [decoded]
        for value in values:
            match = BARCODE_PATTERN.search(str(value or ""))
            if match:
                return match.group(0)
    except Exception:
        logger.exception("Barcode detection failed")
    return None
