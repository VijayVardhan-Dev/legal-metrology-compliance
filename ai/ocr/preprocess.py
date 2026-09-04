import cv2
import numpy as np
import os
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def preprocess_image(image_path: str) -> Tuple[np.ndarray, int, int]:
    """
    Preprocesses an image for OCR.
    Steps:
    1. Read the image
    2. Validate it loaded correctly
    3. Return the loaded image array along with (height, width)

    Returns:
        Tuple of (image_array, image_height, image_width)
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at path: {image_path}")

    # Read image using OpenCV
    img = cv2.imread(image_path)

    if img is None:
        raise ValueError(f"Failed to read image at {image_path}. Might be corrupted or unsupported format.")

    # Standard PaddleOCR expects BGR format as it is usually read by cv2
    # So we don't necessarily need extensive preprocessing yet.
    # Just validate and return the ndarray along with dimensions.
    image_height, image_width = img.shape[:2]

    return img, image_height, image_width
