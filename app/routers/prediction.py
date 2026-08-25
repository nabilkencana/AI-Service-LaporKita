import asyncio
from fastapi import APIRouter, status, Depends
from app.schemas.base import APIResponse
from app.schemas.prediction import (
    PredictRiskRequest,
    PredictRiskData,
    PredictZoneMetricsRequest,
    PredictZoneMetricsData,
    WeatherContextSnapshot,
)
from app.core.logging import logger
from app.core.security import verify_internal_api_key
from app.services.xgboost_service import XGBoostRiskService

router = APIRouter(prefix="/predict-risk", tags=["Risk Prediction"], dependencies=[Depends(verify_internal_api_key)])
zone_metrics_router = APIRouter(prefix="/predict", tags=["Risk Prediction (Zone Metrics)"], dependencies=[Depends(verify_internal_api_key)])


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

    rainfall = (
        payload.rainfall_mm
        if payload.rainfall_mm is not None
        else (payload.weather_context.rainfall_mm if payload.weather_context else 0.0)
    )
    temperature = (
        payload.temperature_c
        if payload.temperature_c is not None
        else (payload.weather_context.temperature_c if payload.weather_context else 27.0)
    )
    drainage_ratio = 0.2
    if payload.category and payload.category.lower() == "drainase":
        drainage_ratio = 0.6
    elif payload.weather_context and payload.weather_context.drainage_issue_ratio is not None:
        drainage_ratio = payload.weather_context.drainage_issue_ratio

    traffic = payload.traffic_density if payload.traffic_density is not None else 0.5

    # Execute real XGBoost inference asynchronously
    xgb_service = XGBoostRiskService.get_instance()
    try:
        flood_prob, risk_level, stress_level, factors, recommendation = await asyncio.to_thread(
            xgb_service.predict_risk,
            report_density=payload.report_density,
            rainfall_mm=rainfall,
            temperature_c=temperature,
            traffic_density=traffic,
            drainage_issue_ratio=drainage_ratio,
        )
    except RuntimeError as re:
        logger.error(f"XGBoost risk service unavailable: {re}")
        from fastapi.responses import JSONResponse
        from app.schemas.base import APIError
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=APIResponse[PredictRiskData](
                success=False,
                data=None,
                error=APIError(
                    code="MODEL_NOT_AVAILABLE",
                    message=str(re),
                ),
            ).model_dump(by_alias=True),
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


@zone_metrics_router.post(
    "/zone-metrics",
    response_model=PredictZoneMetricsData,
    status_code=status.HTTP_200_OK,
    summary="Predict per-zone metrics (compatibility endpoint for NestJS backend-laporkita)",
)
async def predict_zone_metrics(payload: PredictZoneMetricsRequest):
    """
    Compatibility endpoint for the NestJS backend (backend-laporkita).

    Mirrors the contract expected by prediction.service.js:
      request : {zone_id, zone_name, active_reports}
      response: flat {report_density, traffic_density, flood_risk_probability,
                      weather_context, stress_level}

    Uses the same trained XGBoost model as /predict-risk.
    """
    active = payload.active_reports
    rainfall_mm = min(100.0, max(5.0, active * 4.5 + 10.0))
    traffic_density = min(0.95, 0.3 + active * 0.05)

    xgb_service = XGBoostRiskService.get_instance()
    try:
        flood_prob, risk_level, stress_level, _factors, _recommendation = await asyncio.to_thread(
            xgb_service.predict_risk,
            report_density=active,
            rainfall_mm=rainfall_mm,
            traffic_density=traffic_density,
        )
    except RuntimeError as re:
        logger.error(f"Zone metrics XGBoost service unavailable: {re}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": str(re)},
        )

    condition = "Hujan Deras" if rainfall_mm > 40 else "Hujan Ringan / Berawan"

    logger.info(
        f"Received zone-metrics request for zone_id='{payload.zone_id}', "
        f"active_reports={active} -> flood_prob={flood_prob:.4f}, stress={stress_level}"
    )

    return PredictZoneMetricsData(
        report_density=active,
        traffic_density=round(traffic_density, 2),
        flood_risk_probability=flood_prob,
        weather_context=WeatherContextSnapshot(
            rainfall_mm=rainfall_mm,
            condition=condition,
        ),
        stress_level=stress_level,
    )
