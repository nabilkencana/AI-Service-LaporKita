import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_predict_risk_success(client: AsyncClient):
    payload = {
        "zone_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "report_density": 15,
        "weather_context": {
            "rainfall_mm": 45.5,
            "temperature_c": 25.0,
            "condition": "Hujan Lebat"
        },
        "traffic_density": 0.8,
        "category": "Drainase"
    }
    response = await client.post("/v1/predict-risk", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["error"] is None

    result = data["data"]
    assert "flood_risk_probability" in result
    assert 0.0 <= result["flood_risk_probability"] <= 1.0
    assert result["risk_level"] in ["low", "medium", "high"]
    assert result["predicted_stress_level"] in ["low", "medium", "high"]
    assert "factors" in result
    assert len(result["recommendation"]) > 0
    assert result["_placeholder"] is True


@pytest.mark.asyncio
async def test_predict_risk_invalid_traffic(client: AsyncClient):
    # Invalid traffic density > 1.0 -> should trigger 422 with envelope
    payload = {
        "report_density": 5,
        "traffic_density": 1.5
    }
    response = await client.post("/v1/predict-risk", json=payload)
    assert response.status_code == 422

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
