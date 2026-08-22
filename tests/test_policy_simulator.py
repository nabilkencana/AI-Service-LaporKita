import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_policy_simulator_success(client: AsyncClient):
    payload = {
        "prompt_text": "Bagaimana dampak penambahan drainase resapan di kawasan Klojen jika dilakukan serentak?",
        "time_horizon_months": 12,
        "parameters": {
            "budget_idr": 500000000,
            "target_district": "Klojen"
        }
    }
    response = await client.post("/v1/policy-simulate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["error"] is None

    result = data["data"]
    assert "result_narrative" in result
    assert len(result["result_narrative"]) > 20
    assert "result_data" in result
    assert isinstance(result["key_recommendations"], list)
    assert len(result["key_recommendations"]) > 0
    assert result["_placeholder"] is True


@pytest.mark.asyncio
async def test_policy_simulator_prompt_too_short(client: AsyncClient):
    payload = {
        "prompt_text": "Hi"  # min_length is 5
    }
    response = await client.post("/v1/policy-simulate", json=payload)
    assert response.status_code == 422

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
