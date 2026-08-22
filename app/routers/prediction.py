from fastapi import APIRouter, status
from app.schemas.base import APIResponse
from app.schemas.prediction import PredictRiskRequest, PredictRiskData
from app.core.logging import logger
from app.services.xgboost_service import XGBoostRiskService

router = APIRouter(prefix="/predict-risk", tags=["Risk Prediction"])


@router.post(
    "",
    response_model=APIResponse[PredictRiskData],
    status_code=status.HTTP_200_OK,
    summary="Predict flood and infrastructure risk probability using baseline XGBoost model"
)
async def predict_risk(payload: PredictRiskRequest):
    """
    Risk prediction endpoint for Urban Emotion Map and DPUPR/Dishub intervention planning (Rules.md §1.4).
    Uses XGBoost model trained on historical rainfall, report density, and traffic metrics.
    """
    logger.info(f"Received predict-risk request for zone_id='{payload.zone_id}', density={payload.report_density}")

    rainfall = payload.weather_context.rainfall_mm if payload.weather_context else 0.0
    temperature = payload.weather_context.temperature_c if payload.weather_context else 27.0
    drainage_ratio = payload.weather_context.drainage_issue_ratio if payload.weather_context else 0.2
    traffic = payload.traffic_density if payload.traffic_density is not None else 0.5

    # Execute real XGBoost inference
    xgb_service = XGBoostRiskService.get_instance()
    flood_prob, risk_level, stress_level, factors, recommendation = xgb_service.predict_risk(
        report_density=payload.report_density,
        rainfall_mm=rainfall,
        temperature_c=temperature,
        traffic_density=traffic,
        drainage_issue_ratio=drainage_ratio,
    )

    data = PredictRiskData(
        flood_risk_probability=flood_prob,
        risk_level=risk_level,
        predicted_stress_level=stress_level,
        factors=factors,
        recommendation=recommendation,
        is_placeholder=False,
    )

    return APIResponse(
        success=True,
        data=data,
        error=None,
    )
