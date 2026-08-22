from fastapi import APIRouter, status
from app.schemas.base import APIResponse
from app.schemas.verification import VerifyReportRequest, VerifyReportData
from app.core.config import settings
from app.core.logging import logger
from app.utils.gps_validator import is_within_malang_bbox
from app.utils.scoring import calculate_urgency_score

router = APIRouter(prefix="/verify", tags=["AI Verification"])


@router.post(
    "",
    response_model=APIResponse[VerifyReportData],
    status_code=status.HTTP_200_OK,
    summary="Verify report image, classify facility damage, and compute priority score"
)
async def verify_report(payload: VerifyReportRequest):
    """
    AI Verification endpoint for LaporKita report submissions.
    - Validates image against 5 facility classes (YOLOv11-cls).
    - Checks GPS bounds against Kota Malang pilot area.
    - Evaluates confidence threshold >= 0.6 per Rules.md §1.2.
    - Computes Smart Priority urgency score per Rules.md §1.3.
    """
    logger.info(f"Received verification request for category hint='{payload.claimed_category}' at ({payload.latitude}, {payload.longitude})")

    # 1. GPS Validation
    gps_is_valid = is_within_malang_bbox(payload.latitude, payload.longitude)

    # 2. Mock / Placeholder classification results for Phase 1
    predicted_category = payload.claimed_category or payload.device_hint_category or "Jalan Berlubang"
    ai_confidence_score = 0.88 if payload.device_hint_confidence is None else max(0.55, payload.device_hint_confidence)
    damage_severity = 0.75

    # 3. Determine if verification is valid vs needs manual review (Rules.md §1.2)
    # Lolos otomatis jika confidence >= threshold DAN GPS valid
    is_valid = (ai_confidence_score >= settings.AI_CONFIDENCE_THRESHOLD) and gps_is_valid
    needs_manual_review = not is_valid

    # 4. Calculate initial Smart Priority urgency score
    urgency_score = calculate_urgency_score(
        damage_severity=damage_severity,
        support_count=0,
        report_density=5,
        category_name=predicted_category,
    )

    description_auto = f"Terdeteksi kerusakan fasilitas kategori '{predicted_category}' dengan tingkat keparahan estimasi {int(damage_severity * 100)}%."

    data = VerifyReportData(
        ai_confidence_score=round(ai_confidence_score, 4),
        predicted_category=predicted_category,
        is_valid=is_valid,
        needs_manual_review=needs_manual_review,
        damage_severity=damage_severity,
        urgency_score=urgency_score,
        description_auto=description_auto,
        gps_valid=gps_is_valid,
        timestamp_valid=True,
        _placeholder=True,
    )

    return APIResponse(
        success=True,
        data=data,
        error=None,
    )
