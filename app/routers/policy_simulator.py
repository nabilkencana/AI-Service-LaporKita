from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.schemas.base import APIResponse, APIError
from app.schemas.policy_simulator import PolicySimulateRequest, PolicySimulateData
from app.core.logging import logger
from app.services.gemini_service import GeminiPolicyService, GeminiServiceError

router = APIRouter(prefix="/policy-simulate", tags=["Policy Simulator"])


@router.post(
    "",
    response_model=APIResponse[PolicySimulateData],
    status_code=status.HTTP_200_OK,
    summary="Simulate policy intervention outcomes and budget impacts using Gemini LLM"
)
async def simulate_policy(payload: PolicySimulateRequest):
    """
    Policy Simulator endpoint for city planners and agency directors (DPUPR/Dishub) (PRD.md §4.2).
    - Takes policy prompt scenarios (e.g. perbaikan jalan serentak, normalisasi drainase).
    - Projects risk reduction, estimated costs, and strategic recommendations via Gemini LLM.
    """
    logger.info(f"Received policy-simulate request: '{payload.prompt_text[:60]}...'")

    gemini_svc = GeminiPolicyService.get_instance()

    try:
        data = await gemini_svc.simulate_policy(
            prompt_text=payload.prompt_text,
            zone_id=payload.zone_id,
            time_horizon_months=payload.time_horizon_months or 6,
            parameters=payload.parameters,
        )
        return APIResponse(
            success=True,
            data=data,
            error=None,
        )
    except GeminiServiceError as ge:
        logger.error(f"GeminiServiceError in policy simulation: [{ge.code}] {ge.message}")
        http_status = status.HTTP_504_GATEWAY_TIMEOUT if ge.code == "GEMINI_TIMEOUT" else status.HTTP_502_BAD_GATEWAY
        return JSONResponse(
            status_code=http_status,
            content=APIResponse[PolicySimulateData](
                success=False,
                data=None,
                error=APIError(
                    code=ge.code,
                    message=ge.message,
                    details=ge.details,
                ),
            ).model_dump(by_alias=True),
        )
    except Exception as e:
        logger.error(f"Unexpected error in policy simulation: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=APIResponse[PolicySimulateData](
                success=False,
                data=None,
                error=APIError(
                    code="INTERNAL_SERVER_ERROR",
                    message="Gagal memproses simulasi kebijakan publik.",
                    details=[str(e)],
                ),
            ).model_dump(by_alias=True),
        )
