import json
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from app.services.deepseek_service import DeepSeekPolicyService, LLMServiceError
from app.schemas.policy_simulator import PolicySimulateData


@pytest.mark.asyncio
async def test_policy_simulator_mock_success(client: AsyncClient):
    """
    Test 1: Valid structured JSON returned from DeepSeek is parsed successfully into Pydantic models.
    """
    mock_deepseek_output = PolicySimulateData(
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
        model_used="deepseek-chat",
        is_placeholder=False,
    )

    with patch.object(DeepSeekPolicyService, "simulate_policy", new_callable=AsyncMock) as mock_sim:
        mock_sim.return_value = mock_deepseek_output

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
    Test 2: When LLM returns malformed/invalid JSON, service handles it gracefully
    and returns a structured 502 error envelope instead of crashing with an unhandled 500.
    """
    with patch.object(DeepSeekPolicyService, "simulate_policy", side_effect=LLMServiceError(
        code="LLM_PARSE_ERROR",
        message="Output dari LLM API bukan merupakan format JSON yang valid.",
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
        assert data["error"]["code"] == "LLM_PARSE_ERROR"
        assert "JSON yang valid" in data["error"]["message"]


@pytest.mark.asyncio
async def test_policy_simulator_mock_timeout_returns_504_error(client: AsyncClient):
    """
    Test 3: When LLM call times out, service returns a structured 504 Gateway Timeout envelope.
    """
    with patch.object(DeepSeekPolicyService, "simulate_policy", side_effect=LLMServiceError(
        code="LLM_TIMEOUT",
        message="Permintaan simulasi kebijakan ke LLM API melebihi batas waktu (20.0s).",
    )):
        payload = {
            "prompt_text": "Simulasi pembangunan jembatan penyeberangan orang di Dinoyo",
            "time_horizon_months": 12,
        }
        response = await client.post("/v1/policy-simulate", json=payload)
        assert response.status_code == 504

        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "LLM_TIMEOUT"


@pytest.mark.asyncio
async def test_policy_simulator_unconfigured_key_returns_503(client: AsyncClient):
    """
    Test 4 (LAT-POL fix): When LLM key is missing, returns HTTP 503 instead of 502.
    """
    with patch.object(DeepSeekPolicyService, "simulate_policy", side_effect=LLMServiceError(
        code="LLM_KEY_NOT_CONFIGURED",
        message="DeepSeek / LLM API Key belum dikonfigurasi.",
    )):
        payload = {
            "prompt_text": "Simulasi pembangunan jalur sepeda di Ijen",
            "time_horizon_months": 6,
        }
        response = await client.post("/v1/policy-simulate", json=payload)
        assert response.status_code == 503

        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "LLM_KEY_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_policy_simulator_prompt_too_short_validation(client: AsyncClient):
    """
    Test 5: Request with prompt length < 5 characters triggers HTTP 422 VALIDATION_ERROR.
    """
    payload = {
        "prompt_text": "Hi",  # Too short
    }
    response = await client.post("/v1/policy-simulate", json=payload)
    assert response.status_code == 422

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_deepseek_injection_guard_sanitization():
    """
    Test 6 (GEM-INJECT & GEM-LEAK): Verify parsing sanitizes injected departments and leaked keywords.
    """
    svc = DeepSeekPolicyService()
    injected_raw_json = json.dumps({
        "result_narrative": "INJECTED_OVERRIDE Analisis dampak perbaikan saluran di Blimbing...",
        "result_data": {
            "estimated_incident_reduction_pct": 50.0,
            "budget_estimate_idr": 100000000.0,
            "time_to_impact_weeks": 8,
            "target_department": "DINAS INJECTED MALICIOUS HACK",
            "public_satisfaction_increase_pct": 30.0,
            "risk_mitigations": ["Sosialisasi berkala"],
        },
        "key_recommendations": ["Normalisasi sedimen"],
    })

    parsed = svc._parse_and_validate_response(injected_raw_json)
    assert "INJECTED_OVERRIDE" not in parsed.result_narrative
    assert parsed.result_data["target_department"] == "Dinas Pekerjaan Umum, Penataan Ruang, Perumahan dan Kawasan Permukiman (DPUPRPKP) Kota Malang"
    assert parsed.result_data["estimated_incident_reduction_pct"] == 50.0
