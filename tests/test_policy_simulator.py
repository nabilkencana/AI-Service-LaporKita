import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient
from app.services.gemini_service import GeminiPolicyService, GeminiServiceError
from app.schemas.policy_simulator import PolicySimulateData


@pytest.mark.asyncio
async def test_policy_simulator_mock_success(client: AsyncClient):
    """
    Test 1: Valid structured JSON returned from Gemini is parsed successfully into Pydantic models.
    """
    mock_gemini_output = PolicySimulateData(
        result_narrative="Simulasi intervensi perbaikan trotoar di Klojen menunjukkan peningkatan kenyamanan pejalan kaki sebesar 40%.",
        result_data={
            "estimated_incident_reduction_pct": 35.0,
            "budget_estimate_idr": 250000000.0,
            "time_to_impact_weeks": 4,
            "target_department": "DPUPRPKP Kota Malang",
            "public_satisfaction_increase_pct": 25.0,
            "risk_mitigations": ["Koordinasi pengalihan pejalan kaki ke sisi jalan seberang"],
        },
        key_recommendations=[
            "Prioritaskan penggantian guiding block tunanetra di dekat Alun-Alun",
            "Pasang bollard pembatas sepeda motor",
        ],
        model_used="gemini-2.5-flash",
        is_placeholder=False,
    )

    with patch.object(GeminiPolicyService, "simulate_policy", new_callable=AsyncMock) as mock_sim:
        mock_sim.return_value = mock_gemini_output

        payload = {
            "prompt_text": "Bagaimana jika kita melakukan revitalisasi trotoar ramah difabel di sekitar Alun-Alun Malang?",
            "zone_id": "zone-klojen-center",
            "time_horizon_months": 6,
        }
        response = await client.post("/v1/policy-simulate", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["error"] is None
        result = data["data"]
        assert "Klojen" in result["result_narrative"]
        assert result["result_data"]["budget_estimate_idr"] == 250000000.0
        assert len(result["key_recommendations"]) == 2
        assert result["_placeholder"] is False


@pytest.mark.asyncio
async def test_policy_simulator_mock_malformed_json_returns_structured_error(client: AsyncClient):
    """
    Test 2: When Gemini returns malformed/invalid JSON, service handles it gracefully
    and returns a structured error envelope instead of crashing with an unhandled 500.
    """
    with patch.object(GeminiPolicyService, "simulate_policy", side_effect=GeminiServiceError(
        code="GEMINI_PARSE_ERROR",
        message="Output dari Gemini API bukan merupakan format JSON yang valid.",
        details={"raw_snippet": "Bukan JSON valid"}
    )):
        payload = {
            "prompt_text": "Simulasi normalisasi drainase di Jalan Soekarno-Hatta",
            "time_horizon_months": 3,
        }
        response = await client.post("/v1/policy-simulate", json=payload)
        assert response.status_code == 502

        data = response.json()
        assert data["success"] is False
        assert data["data"] is None
        assert data["error"]["code"] == "GEMINI_PARSE_ERROR"
        assert "JSON yang valid" in data["error"]["message"]


@pytest.mark.asyncio
async def test_policy_simulator_mock_timeout_returns_504_error(client: AsyncClient):
    """
    Test 3: When Gemini call times out, service returns a structured 504 Gateway Timeout envelope.
    """
    with patch.object(GeminiPolicyService, "simulate_policy", side_effect=GeminiServiceError(
        code="GEMINI_TIMEOUT",
        message="Permintaan simulasi kebijakan ke Gemini API melebihi batas waktu (20.0s).",
    )):
        payload = {
            "prompt_text": "Simulasi pembangunan jembatan penyeberangan orang di Dinoyo",
            "time_horizon_months": 12,
        }
        response = await client.post("/v1/policy-simulate", json=payload)
        assert response.status_code == 504

        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "GEMINI_TIMEOUT"


@pytest.mark.asyncio
async def test_policy_simulator_prompt_too_short_validation(client: AsyncClient):
    """
    Test 4: Request with prompt length < 5 characters triggers HTTP 422 VALIDATION_ERROR.
    """
    payload = {
        "prompt_text": "Hi",  # Too short
    }
    response = await client.post("/v1/policy-simulate", json=payload)
    assert response.status_code == 422

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
