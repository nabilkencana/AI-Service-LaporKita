from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from app.schemas.base import APIResponse, APIError
from app.schemas.policy_simulator import PolicySimulateRequest, PolicySimulateData
from app.core.logging import logger
from app.core.security import verify_internal_api_key
from app.services.deepseek_service import DeepSeekPolicyService, LLMServiceError
from app.services.gemini_service import GeminiServiceError

router = APIRouter(prefix="/policy-simulate", tags=["Policy Simulator"], dependencies=[Depends(verify_internal_api_key)])


@router.post(
    "",
    response_model=APIResponse[PolicySimulateData],
    status_code=status.HTTP_200_OK,
    summary="Simulate policy intervention outcomes and budget impacts using DeepSeek LLM"
)
async def simulate_policy(payload: PolicySimulateRequest):
    """
    Policy Simulator endpoint for city planners and agency directors (DPUPR/Dishub) (PRD.md §4.2).
    - Takes policy prompt scenarios (e.g. perbaikan jalan serentak, normalisasi drainase).
    - Projects risk reduction, estimated costs, and strategic recommendations via DeepSeek LLM.
    """
    logger.info(f"Received policy-simulate request: '{payload.prompt_text[:60]}...'")

    llm_svc = DeepSeekPolicyService.get_instance()

    try:
        data = await llm_svc.simulate_policy(
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
    except (LLMServiceError, GeminiServiceError) as ge:
        logger.error(f"LLMServiceError in policy simulation: [{ge.code}] {ge.message}")
        if ge.code in ("LLM_TIMEOUT", "GEMINI_TIMEOUT"):
            http_status = status.HTTP_504_GATEWAY_TIMEOUT
        elif ge.code in ("LLM_KEY_NOT_CONFIGURED", "GEMINI_KEY_NOT_CONFIGURED"):
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            http_status = status.HTTP_502_BAD_GATEWAY

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
