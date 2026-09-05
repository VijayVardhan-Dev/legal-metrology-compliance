import logging
import os
import time
from typing import Dict, Any

# ── CRITICAL: must be set before any paddle / paddleocr import ──────────
# PaddlePaddle 3.3 + oneDNN on Windows crashes with the new PIR engine
# ("ConvertPirAttribute2RuntimeAttribute not support").
# Disabling PIR and oneDNN/mkldnn forces the reliable legacy CPU execution path.
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

logger = logging.getLogger(__name__)

# Lazy initialization of the OCR model
_ocr_engine = None


def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        logger.info("Initializing PaddleOCR engine (v3.x mobile models)...")
        from paddleocr import PaddleOCR

        # PaddleOCR 3.x constructor:
        #   - No show_log / use_angle_cls (v2 args removed)
        #   - use_textline_orientation replaces use_angle_cls
        #   - Use mobile models so local CPU startup is practical
        #   - Disable orientation and unwarping models for package-label OCR
        _ocr_engine = PaddleOCR(
            use_textline_orientation=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            text_detection_model_name="PP-OCRv5_mobile_det",
            text_recognition_model_name="PP-OCRv5_mobile_rec",
        )
        logger.info("PaddleOCR engine initialized.")
    return _ocr_engine


def extract_text_from_image(image_array) -> Dict[str, Any]:
    """
    Runs PaddleOCR 3.x on the provided image array and returns the raw result.

    PaddleOCR 3.x returns an OCRResult object with:
        rec_texts:   List[str]           — recognized text strings
        rec_scores:  List[float]         — recognition confidence per text
        dt_polys:    List[np.ndarray]    — detection polygons (Nx2 arrays)
        dt_scores:   List[float]         — detection confidence per polygon
    """
    engine = get_ocr_engine()

    start_time = time.time()
    # .predict() returns a generator; for a single ndarray we get one OCRResult
    results = list(engine.predict(image_array))
    end_time = time.time()

    processing_time_ms = int((end_time - start_time) * 1000)

    return {
        "raw_result": results,
        "processing_time_ms": processing_time_ms,
    }
