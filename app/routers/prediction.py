from fastapi import APIRouter, status
from app.schemas.base import APIResponse
from app.schemas.prediction import PredictRiskRequest, PredictRiskData
from app.core.logging import logger

router = APIRouter(prefix="/predict-risk", tags=["Risk Prediction"])


@router.post(
    "",
    response_model=APIResponse[PredictRiskData],
    status_code=status.HTTP_200_OK,
    summary="Predict flood and infrastructure risk probability using XGBoost model"
)
async def predict_risk(payload: PredictRiskRequest):
    """
    Risk prediction endpoint for Urban Emotion Map and DPUPR/Dishub intervention planning.
    - Uses report density, weather conditions, and traffic density.
    - Estimates flood risk probability and urban stress level (low, medium, high).
    """
    logger.info(f"Received predict-risk request for zone_id='{payload.zone_id}', density={payload.report_density}")

    # Mock / Placeholder risk calculation for Phase 1
    rainfall = payload.weather_context.rainfall_mm if payload.weather_context else 0.0
    traffic = payload.traffic_density if payload.traffic_density is not None else 0.5

    # Simple heuristic to provide realistic dummy probability
    prob = min(0.95, max(0.05, (payload.report_density * 0.03) + (rainfall * 0.008) + (traffic * 0.2)))

    if prob >= 0.7:
        risk_level = "high"
        stress_level = "high"
        recommendation = "Prioritaskan pembersihan saluran drainase dan siagakan pompa air bergerak di titik rawan genangan."
    elif prob >= 0.4:
        risk_level = "medium"
        stress_level = "medium"
        recommendation = "Lakukan pemantauan rutin pada sedimentasi drainase dan rekayasa arus lalu lintas ringan."
    else:
        risk_level = "low"
        stress_level = "low"
        recommendation = "Kondisi zona terpantau aman dan terkendali. Lanjutkan pemeliharaan preventif berkala."

    data = PredictRiskData(
        flood_risk_probability=round(prob, 4),
        risk_level=risk_level,
        predicted_stress_level=stress_level,
        factors={
            "report_density_weight": round(payload.report_density * 0.03, 3),
            "rainfall_impact": round(rainfall * 0.008, 3),
            "traffic_density_impact": round(traffic * 0.2, 3),
        },
        recommendation=recommendation,
        _placeholder=True,
    )

    return APIResponse(
        success=True,
        data=data,
        error=None,
    )
