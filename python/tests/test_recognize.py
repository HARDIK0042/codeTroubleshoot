import io

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.preprocessing.image_ops import preprocess_image, resize_image
from app.utils.files import read_result, write_result
from app.recognition.ocr import prepare_for_ocr, tesseract_config
from app.utils.text import format_recognized_text


def png_bytes(width=80, height=40):
    image = Image.new("RGB", (width, height), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def jpeg_bytes():
    image = Image.new("RGB", (80, 40), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_homepage():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Process" in response.text
    assert "Copy text" in response.text
    assert "Download text" in response.text


def test_recognize_png(monkeypatch, tmp_path):
    monkeypatch.setenv("RESULT_DIR", str(tmp_path))
    monkeypatch.setattr(
        "app.recognition.ocr.pytesseract.image_to_string",
        lambda image, lang="eng", config="": "Hello",
    )
    client = TestClient(app)
    response = client.post(
        "/api/recognize",
        files={"file": ("note.png", png_bytes(), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["text"], str)
    assert isinstance(body["processing_ms"], (int, float))
    assert body["filename"] == "note.png"
    download = client.get(f"/api/results/{body['id']}/download")
    assert download.status_code == 200
    assert download.text == "Hello"
    processed = client.get(f"/api/results/{body['id']}/processed.png")
    assert processed.status_code == 200
    assert processed.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_read_result_does_not_truncate_saved_text(monkeypatch, tmp_path):
    monkeypatch.setenv("RESULT_DIR", str(tmp_path))
    write_result("a" * 32, "saved result")
    assert read_result("a" * 32) == "saved result"


def test_resize_preserves_aspect_ratio_without_upscaling():
    image = np.zeros((100, 200, 3), dtype=np.uint8)
    resized = resize_image(image, max_width=80, max_height=60)
    assert resized.shape[:2] == (40, 80)


def test_resize_keeps_normal_resolution_images_unchanged():
    image = np.zeros((1200, 1400, 3), dtype=np.uint8)
    resized = resize_image(image)
    assert resized.shape[:2] == (600, 700)


def test_preprocess_preserves_grayscale_text_image():
    image = np.full((60, 100, 3), 255, dtype=np.uint8)
    image[20:40, 30:70] = 0
    processed = preprocess_image(image)
    assert processed.shape == (60, 100)
    assert processed.dtype == np.uint8
    assert processed[5, 5] == 0
    assert processed[30, 50] == 255


def test_ocr_uses_document_segmentation_mode():
    assert tesseract_config() == "--oem 3 --psm 11"


def test_ocr_uses_upscaled_grayscale_original():
    image = np.zeros((40, 80, 3), dtype=np.uint8)
    image[:, :] = 255
    prepared = prepare_for_ocr(image, np.zeros((40, 80), dtype=np.uint8))
    assert prepared.shape == (120, 240)
    assert prepared.ndim == 2


def test_recognized_text_keeps_line_breaks():
    assert format_recognized_text(" First line \n\n Second line ") == "First line\nSecond line"


def test_recognized_text_restores_button_word_spacing():
    assert format_recognized_text("Send yournote") == "Send your note"


def test_pipeline_passes_preprocessed_image_to_ocr(monkeypatch):
    from app.services import pipeline

    source = np.zeros((40, 80, 3), dtype=np.uint8)
    binary = np.full((40, 80), 255, dtype=np.uint8)
    received = {}
    monkeypatch.setattr(pipeline, "decode_image", lambda data: source)
    monkeypatch.setattr(pipeline, "resize_image", lambda image: source)
    monkeypatch.setattr(pipeline, "preprocess_image", lambda image: binary)

    def capture_ocr_input(original, preprocessed):
        received["image"] = preprocessed
        return preprocessed

    monkeypatch.setattr(pipeline, "prepare_for_ocr", capture_ocr_input)
    monkeypatch.setattr(pipeline, "extract_text", lambda image, config: "OK")
    outcome = pipeline.run_pipeline(b"image")
    assert received["image"] is binary
    assert outcome["text"] == "OK"


def test_recognize_jpeg(monkeypatch, tmp_path):
    monkeypatch.setenv("RESULT_DIR", str(tmp_path))
    monkeypatch.setattr(
        "app.recognition.ocr.pytesseract.image_to_string",
        lambda image, lang="eng", config="": "Hello",
    )
    client = TestClient(app)
    response = client.post(
        "/api/recognize",
        files={"file": ("scan.jpg", jpeg_bytes(), "image/jpeg")},
    )
    assert response.status_code == 200
    assert isinstance(response.json()["text"], str)


def test_recognize_reports_when_no_text_was_detected(monkeypatch):
    monkeypatch.setattr(
        "app.routes.recognize.run_pipeline",
        lambda data: {"text": "", "processing_ms": 1, "processed_png": b"image"},
    )
    client = TestClient(app)
    response = client.post(
        "/api/recognize",
        files={"file": ("note.png", png_bytes(), "image/png")},
    )
    assert response.status_code == 422
    assert response.json()["error"].startswith("No text was detected.")


def test_missing_file():
    client = TestClient(app)
    response = client.post("/api/recognize")
    assert response.status_code == 422


def test_rejects_pdf():
    client = TestClient(app)
    response = client.post(
        "/api/recognize",
        files={"file": ("notes.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 400


def test_rejects_png_with_wrong_content():
    client = TestClient(app)
    response = client.post(
        "/api/recognize",
        files={"file": ("note.png", b"not-an-image", "image/png")},
    )
    assert response.status_code == 400


def test_rejects_oversized_image():
    client = TestClient(app)
    payload = png_bytes() + b"0" * (5 * 1024 * 1024)
    response = client.post(
        "/api/recognize",
        files={"file": ("large.png", payload, "image/png")},
    )
    assert response.status_code == 400


def test_rejects_path_filename(monkeypatch, tmp_path):
    monkeypatch.setenv("RESULT_DIR", str(tmp_path))
    client = TestClient(app)
    response = client.post(
        "/api/recognize",
        files={"file": ("../../secret.png", png_bytes(), "image/png")},
    )
    assert response.status_code == 400
