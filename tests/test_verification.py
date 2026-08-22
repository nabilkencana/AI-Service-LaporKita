import base64
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from httpx import AsyncClient

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

    # Fallback minimal 64x64 valid JPEG image
    from PIL import Image
    import io
    img = Image.new("RGB", (64, 64), color=(128, 128, 128))
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
    assert result["is_valid"] is True
    assert result["needs_manual_review"] is False
    assert result["_placeholder"] is False
    assert len(result["description_auto"]) > 10


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
async def test_verify_report_all_5_classes_inference(client: AsyncClient):
    """
    Scenario 4: Test inference on all 5 classes with real test set samples.
    """
    classes = ["Jalan Berlubang", "Trotoar", "Rambu Lalu Lintas", "Lampu Jalan", "Drainase"]

    for cls in classes:
        img_b64 = get_sample_test_image_base64(cls)
        payload = {
            "image_base64": img_b64,
            "claimed_category": cls,
            "latitude": -7.9826,
            "longitude": 112.6308,
        }
        response = await client.post("/v1/verify", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        result = data["data"]
        assert result["predicted_category"] in classes
        assert 0.0 <= result["ai_confidence_score"] <= 1.0
        assert 0.0 <= result["damage_severity"] <= 1.0
        assert 0.0 <= result["urgency_score"] <= 1.0
        assert result["_placeholder"] is False


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
