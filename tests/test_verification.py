import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_verify_report_success(client: AsyncClient):
    payload = {
        "image_url": "https://storage.laporkita.id/reports/photo123.jpg",
        "claimed_category": "Jalan Berlubang",
        "latitude": -7.9826,
        "longitude": 112.6308,
        "device_hint_category": "Jalan Berlubang",
        "device_hint_confidence": 0.92,
    }
    response = await client.post("/v1/verify", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["error"] is None

    result = data["data"]
    assert result["predicted_category"] == "Jalan Berlubang"
    assert result["ai_confidence_score"] >= 0.6
    assert result["is_valid"] is True
    assert result["needs_manual_review"] is False
    assert result["gps_valid"] is True
    assert result["damage_severity"] > 0
    assert result["urgency_score"] > 0
    assert result["_placeholder"] is True


@pytest.mark.asyncio
async def test_verify_report_outside_malang(client: AsyncClient):
    # Location outside Malang (e.g. Surabaya -7.2575, 112.7521)
    payload = {
        "image_url": "https://storage.laporkita.id/reports/photo_surabaya.jpg",
        "claimed_category": "Lampu Jalan",
        "latitude": -7.2575,
        "longitude": 112.7521,
    }
    response = await client.post("/v1/verify", json=payload)
    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    assert result["gps_valid"] is False
    assert result["is_valid"] is False
    assert result["needs_manual_review"] is True


@pytest.mark.asyncio
async def test_verify_report_missing_image(client: AsyncClient):
    # Neither image_url nor image_base64 provided -> should return 422 with envelope
    payload = {
        "claimed_category": "Trotoar",
        "latitude": -7.9826,
        "longitude": 112.6308,
    }
    response = await client.post("/v1/verify", json=payload)
    assert response.status_code == 422

    data = response.json()
    assert data["success"] is False
    assert data["data"] is None
    assert data["error"]["code"] == "VALIDATION_ERROR"
