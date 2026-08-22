import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_with_models_status(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["error"] is None
    data = payload["data"]
    assert data["status"] == "ok"
    assert data["service"] == "ai-service"
    assert data["version"] == "1.0.0"

    # Verify models loaded status
    assert data["models"] is not None
    assert data["models"]["yolo_classification_loaded"] is True
    assert data["models"]["xgboost_risk_loaded"] is True
    assert "gemini_configured" in data["models"]
