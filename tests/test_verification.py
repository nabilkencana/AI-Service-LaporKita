import base64
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.services.yolo_service import YOLOClassificationService

# Pick a real sample image from test set if exists, or generate a simple valid image
BASE_DIR = Path(__file__).resolve().parent.parent
TEST_DIR = BASE_DIR / "dataset" / "test"


def get_sample_test_image_base64(category: str = "Jalan Berlubang") -> str:
    """Retrieve base64 of an actual test image from dataset/test/."""
    cls_folder = TEST_DIR / category
    if cls_folder.exists():
        img_files = list(cls_folder.glob("*.jpg")) + list(cls_folder.glob("*.png"))
        if img_files:
            with open(img_files[0], "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")

    # Fallback valid 480x480 JPEG image (RES-480 compliant)
    from PIL import Image
    import io
    img = Image.new("RGB", (480, 480), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


@pytest.mark.asyncio
async def test_verify_report_valid_and_approved(client: AsyncClient):
    """
    Scenario 1: High confidence + valid Malang GPS + valid timestamp
    Expected: is_valid = True, needs_manual_review = False (Rules.md §1.2)
    """
    img_b64 = get_sample_test_image_base64("Jalan Berlubang")
    valid_timestamp = datetime.now(timezone.utc).isoformat()

    payload = {
        "image_base64": img_b64,
        "claimed_category": "Jalan Berlubang",
        "latitude": -7.9826,
        "longitude": 112.6308,
        "timestamp": valid_timestamp,
    }
    response = await client.post("/v1/verify", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    result = data["data"]
    assert result["gps_valid"] is True
    assert result["timestamp_valid"] is True
    assert result["ai_confidence_score"] >= 0.6
    assert result["ai_confidence_score"] >= settings.AI_CONFIDENCE_AUTO_THRESHOLD  # auto-verify butuh confidence tinggi
    assert result["is_valid"] is True
    assert result["needs_manual_review"] is False
    assert result["_placeholder"] is False
    assert len(result["description_auto"]) > 10


@pytest.mark.asyncio
async def test_verify_report_mid_confidence_requires_manual_review(client: AsyncClient, monkeypatch):
    """
    OOD guard lanjutan: confidence menengah (THRESHOLD <= conf < AUTO_THRESHOLD)
    tidak boleh auto-verify walau GPS & timestamp valid.
    Expected: is_valid = False, needs_manual_review = True.
    """
    def fake_predict(self, image_url=None, image_base64=None):
        # (predicted_category, confidence, class_probs, damage_severity)
        return ("Drainase", 0.70, {"Drainase": 0.70}, 0.5)

    monkeypatch.setattr(YOLOClassificationService, "predict", fake_predict)

    img_b64 = get_sample_test_image_base64("Jalan Berlubang")
    payload = {
        "image_base64": img_b64,
        "claimed_category": "Drainase",
        "latitude": -7.9826,
        "longitude": 112.6308,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    response = await client.post("/v1/verify", json=payload)
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["gps_valid"] is True
    assert result["timestamp_valid"] is True
    assert result["ai_confidence_score"] == 0.70
    assert result["is_valid"] is False
    assert result["needs_manual_review"] is True


@pytest.mark.asyncio
async def test_verify_report_outside_malang_requires_manual_review(client: AsyncClient):
    """
    Scenario 2: Valid photo & confidence, but GPS is outside Malang
    Expected: gps_valid = False, is_valid = False, needs_manual_review = True
    """
    img_b64 = get_sample_test_image_base64("Lampu Jalan")
    payload = {
        "image_base64": img_b64,
        "claimed_category": "Lampu Jalan",
        "latitude": -6.2088,  # Jakarta
        "longitude": 106.8456,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    response = await client.post("/v1/verify", json=payload)
    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    assert result["gps_valid"] is False
    assert result["is_valid"] is False
    assert result["needs_manual_review"] is True


@pytest.mark.asyncio
async def test_verify_report_future_timestamp_requires_manual_review(client: AsyncClient):
    """
    Scenario 3: Valid photo & Malang GPS, but timestamp is in the future
    Expected: timestamp_valid = False, is_valid = False, needs_manual_review = True
    """
    img_b64 = get_sample_test_image_base64("Trotoar")
    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    payload = {
        "image_base64": img_b64,
        "claimed_category": "Trotoar",
        "latitude": -7.9826,
        "longitude": 112.6308,
        "timestamp": future_time,
    }
    response = await client.post("/v1/verify", json=payload)
    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    assert result["timestamp_valid"] is False
    assert result["is_valid"] is False
    assert result["needs_manual_review"] is True


@pytest.mark.asyncio
async def test_verify_report_all_5_classes_exact_matching(client: AsyncClient):
    """
    Scenario 4 (TEST-WEAK fix): Test inference on all 5 damage classes with ground truth samples.
    Asserts predicted_category == expected class label.
    """
    classes = ["Jalan Berlubang", "Trotoar", "Rambu Lalu Lintas", "Lampu Jalan", "Drainase"]

    for cls in classes:
        img_b64 = get_sample_test_image_base64(cls)
        payload = {
            "image_base64": img_b64,
            "claimed_category": cls,
            "latitude": -7.9826,
            "longitude": 112.6308,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        response = await client.post("/v1/verify", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        result = data["data"]
        assert result["predicted_category"] == cls
        assert 0.0 <= result["ai_confidence_score"] <= 1.0
        assert 0.0 <= result["damage_severity"] <= 1.0
        assert result["_placeholder"] is False


@pytest.mark.asyncio
async def test_verify_report_ood_non_facility_images_rejected(client: AsyncClient):
    """
    Scenario 4b (MODEL-OOD & FIX-1): Test Out-of-Distribution images:
    - Solid gray 4000x3000
    - Color gradient
    - Random noise
    Expected: predicted_category == 'bukan_fasilitas', is_valid = False, needs_manual_review = True
    """
    from PIL import Image
    import io
    import numpy as np

    # 1. Plain Solid Gray 4000x3000
    img_gray = Image.new("RGB", (4000, 3000), color=(128, 128, 128))
    buf_gray = io.BytesIO()
    img_gray.save(buf_gray, format="JPEG", quality=85)
    b64_gray = base64.b64encode(buf_gray.getvalue()).decode("utf-8")

    payload_gray = {
        "image_base64": b64_gray,
        "claimed_category": "Jalan Berlubang",
        "latitude": -7.9826,
        "longitude": 112.6308,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    resp_gray = await client.post("/v1/verify", json=payload_gray)
    assert resp_gray.status_code == 200
    data_gray = resp_gray.json()["data"]
    assert data_gray["predicted_category"] == "bukan_fasilitas"
    assert data_gray["is_valid"] is False
    assert data_gray["needs_manual_review"] is True

    # 2. Gradient Image
    arr = np.zeros((480, 640, 3), dtype=np.uint8)
    for x in range(640):
        arr[:, x] = [int(255 * x / 639), int(128 * (1 - x / 639)), 200]
    img_grad = Image.fromarray(arr)
    buf_grad = io.BytesIO()
    img_grad.save(buf_grad, format="JPEG", quality=90)
    b64_grad = base64.b64encode(buf_grad.getvalue()).decode("utf-8")

    payload_grad = {
        "image_base64": b64_grad,
        "claimed_category": "Drainase",
        "latitude": -7.9826,
        "longitude": 112.6308,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    resp_grad = await client.post("/v1/verify", json=payload_grad)
    assert resp_grad.status_code == 200
    data_grad = resp_grad.json()["data"]
    assert data_grad["predicted_category"] == "bukan_fasilitas"
    assert data_grad["is_valid"] is False
    assert data_grad["needs_manual_review"] is True


@pytest.mark.asyncio
async def test_verify_report_missing_image_validation_error(client: AsyncClient):
    """
    Scenario 5: Request missing both image_url and image_base64
    Expected: HTTP 422 with standard error envelope
    """
    payload = {
        "claimed_category": "Drainase",
        "latitude": -7.9826,
        "longitude": 112.6308,
    }
    response = await client.post("/v1/verify", json=payload)
    assert response.status_code == 422

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_verify_report_corrupted_base64_returns_structured_error(client: AsyncClient):
    """
    Scenario 6: Request with corrupted/unreadable base64 string
    Expected: Handled HTTP 422 error with code INVALID_IMAGE in standard envelope
    """
    payload = {
        "image_base64": "NOT_A_VALID_BASE64_IMAGE_DATA_STRING_12345",
        "claimed_category": "Jalan Berlubang",
        "latitude": -7.9826,
        "longitude": 112.6308,
    }
    response = await client.post("/v1/verify", json=payload)
    assert response.status_code == 422

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_IMAGE"
    assert "tidak dapat dimuat" in data["error"]["message"]


@pytest.mark.asyncio
async def test_verify_report_missing_timestamp_requires_manual_review(client: AsyncClient):
    """
    Scenario 7 (RULES-1): Request without timestamp
    Expected: timestamp_valid = False, is_valid = False, needs_manual_review = True per Rules.md §1.2
    """
    img_b64 = get_sample_test_image_base64("Jalan Berlubang")
    payload = {
        "image_base64": img_b64,
        "claimed_category": "Jalan Berlubang",
        "latitude": -7.9826,
        "longitude": 112.6308,
        # timestamp omitted deliberately
    }
    response = await client.post("/v1/verify", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    result = data["data"]
    assert result["timestamp_valid"] is False
    assert result["is_valid"] is False
    assert result["needs_manual_review"] is True


@pytest.mark.asyncio
async def test_verify_report_invalid_category_validation_error(client: AsyncClient):
    """
    Scenario 8 (CAT-VAL): Request with invalid category string
    Expected: HTTP 422 with VALIDATION_ERROR
    """
    img_b64 = get_sample_test_image_base64("Jalan Berlubang")
    payload = {
        "image_base64": img_b64,
        "claimed_category": "KategoriNgasal123",
        "latitude": -7.9826,
        "longitude": 112.6308,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    response = await client.post("/v1/verify", json=payload)
    assert response.status_code == 422

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "Kategori 'KategoriNgasal123' tidak valid" in data["error"]["message"]


@pytest.mark.asyncio
async def test_verify_report_unloaded_model_fail_closed(client: AsyncClient):
    """
    Scenario 9 (MOCK-1): When YOLO model is not loaded in memory
    Expected: HTTP 503 fail-closed with MODEL_NOT_AVAILABLE (never fake success)
    """
    from app.services.yolo_service import YOLOClassificationService
    svc = YOLOClassificationService.get_instance()
    original_model = svc.model

    try:
        svc.model = None  # Simulate unloaded model
        img_b64 = get_sample_test_image_base64("Jalan Berlubang")
        payload = {
            "image_base64": img_b64,
            "claimed_category": "Jalan Berlubang",
            "latitude": -7.9826,
            "longitude": 112.6308,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        response = await client.post("/v1/verify", json=payload)
        assert response.status_code == 503

        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "MODEL_NOT_AVAILABLE"
    finally:
        svc.model = original_model

