import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_predict_risk_success(client: AsyncClient):
    """
    Test standard predict-risk request and verify real XGBoost output schema and bounds.
    """
    payload = {
        "zone_id": "zone-klojen-01",
        "report_density": 15,
        "weather_context": {
            "rainfall_mm": 35.0,
            "temperature_c": 24.5,
            "condition": "Hujan Sedang",
            "drainage_issue_ratio": 0.35,
        },
        "traffic_density": 0.7,
        "category": "Drainase",
    }
    response = await client.post("/v1/predict-risk", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    result = data["data"]
    assert 0.0 <= result["flood_risk_probability"] <= 1.0
    assert result["risk_level"] in ["low", "medium", "high"]
    assert result["predicted_stress_level"] in ["low", "medium", "high"]
    assert len(result["recommendation"]) > 10
    assert result["_placeholder"] is False


@pytest.mark.asyncio
async def test_predict_risk_high_vs_low_environmental_stress(client: AsyncClient):
    """
    Sanity Check Model Direction:
    High rainfall (80mm) & high density (35) MUST produce a higher flood_risk_probability
    than low rainfall (0mm) & low density (1).
    """
    high_stress_payload = {
        "zone_id": "zone-high-stress",
        "report_density": 35,
        "weather_context": {
            "rainfall_mm": 80.0,
            "temperature_c": 22.0,
            "drainage_issue_ratio": 0.6,
        },
        "traffic_density": 0.85,
    }
    low_stress_payload = {
        "zone_id": "zone-low-stress",
        "report_density": 1,
        "weather_context": {
            "rainfall_mm": 0.0,
            "temperature_c": 30.0,
            "drainage_issue_ratio": 0.05,
        },
        "traffic_density": 0.2,
    }

    resp_high = await client.post("/v1/predict-risk", json=high_stress_payload)
    resp_low = await client.post("/v1/predict-risk", json=low_stress_payload)

    assert resp_high.status_code == 200
    assert resp_low.status_code == 200

    prob_high = resp_high.json()["data"]["flood_risk_probability"]
    prob_low = resp_low.json()["data"]["flood_risk_probability"]

    assert prob_high > prob_low
    assert prob_high >= 0.65  # Expected high risk
    assert prob_low <= 0.35   # Expected low risk


@pytest.mark.asyncio
async def test_predict_risk_invalid_traffic(client: AsyncClient):
    """
    Test validation error when traffic_density is outside [0.0, 1.0].
    """
    payload = {
        "report_density": 10,
        "traffic_density": 1.5,  # Invalid: > 1.0
    }
    response = await client.post("/v1/predict-risk", json=payload)
    assert response.status_code == 422

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
