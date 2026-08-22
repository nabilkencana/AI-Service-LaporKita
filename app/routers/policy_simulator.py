from fastapi import APIRouter, status
from app.schemas.base import APIResponse
from app.schemas.policy_simulator import PolicySimulateRequest, PolicySimulateData
from app.core.config import settings
from app.core.logging import logger

router = APIRouter(prefix="/policy-simulate", tags=["Policy Simulator"])


@router.post(
    "",
    response_model=APIResponse[PolicySimulateData],
    status_code=status.HTTP_200_OK,
    summary="Simulate policy intervention outcomes and budget impacts using LLM"
)
async def simulate_policy(payload: PolicySimulateRequest):
    """
    Policy Simulator endpoint for city planners and agency directors (DPUPR/Dishub).
    - Takes policy prompt scenarios (e.g. perbaikan jalan serentak, normalisasi drainase).
    - Projects risk reduction, estimated costs, and strategic recommendations.
    """
    logger.info(f"Received policy-simulate request: '{payload.prompt_text[:60]}...'")

    # Mock / Placeholder narrative response for Phase 1
    narrative = (
        f"Berdasarkan skenario '{payload.prompt_text}' dengan horizon waktu {payload.time_horizon_months} bulan, "
        "simulasi menunjukkan potensi penurunan keluhan warga hingga 42% pada koridor terdampak. "
        "Intervensi terkoordinasi antara DPUPR dan Dishub diproyeksikan mengoptimalkan efisiensi anggaran perbaikan sebesar 18%."
    )

    result_data = {
        "time_horizon_months": payload.time_horizon_months,
        "projected_complaint_reduction_pct": 42.5,
        "estimated_budget_idr": 450000000,
        "high_priority_zones_count": 3,
        "estimated_completion_weeks": 8,
    }

    key_recommendations = [
        "Jadwalkan pengerjaan perbaikan drainase sebelum puncak musim hujan bulan November-Desember.",
        "Sinergikan penutupan lajur jalan sementara dengan rute alternatif Dishub untuk meminimalisir lonjakan kemacetan.",
        "Prioritaskan pengadaan material aspal cold-mix untuk penambalan cepat lubang kritis dalam radius 500m dari sekolah.",
    ]

    data = PolicySimulateData(
        result_narrative=narrative,
        result_data=result_data,
        key_recommendations=key_recommendations,
        model_used=settings.GEMINI_MODEL_NAME,
        _placeholder=True,
    )

    return APIResponse(
        success=True,
        data=data,
        error=None,
    )
