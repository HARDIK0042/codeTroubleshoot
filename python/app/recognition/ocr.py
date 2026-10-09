import os

import cv2
import pytesseract

from app.preprocessing.image_ops import to_grayscale


def configure_tesseract():
    command = os.environ.get("TESSERACT_CMD")
    if command:
        pytesseract.pytesseract.tesseract_cmd = command
        return
    default = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default):
        pytesseract.pytesseract.tesseract_cmd = default


def tesseract_config():
    return "--oem 3 --psm 11"


def prepare_for_ocr(original, preprocessed):
    gray = to_grayscale(original)
    height, width = gray.shape[:2]
    scale = min(3, 2400 / max(height, width))
    if scale <= 1:
        return gray
    return cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)


def extract_text(image, config):
    configure_tesseract()
    return pytesseract.image_to_string(image, lang="eng", config=config)
