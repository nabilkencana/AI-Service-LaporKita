import asyncio
from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from app.schemas.base import APIResponse, APIError
from app.schemas.verification import VerifyReportRequest, VerifyReportData, VerifyReportNestJSData
from app.core.config import settings
from app.core.logging import logger
from app.core.security import verify_internal_api_key
from app.services.yolo_service import YOLOClassificationService
from app.utils.gps_validator import is_within_malang_bbox, validate_report_timestamp

router = APIRouter(prefix="/verify", tags=["AI Verification"], dependencies=[Depends(verify_internal_api_key)])
verify_compat_router = APIRouter(prefix="/verify", tags=["AI Verification (NestJS Compat)"], dependencies=[Depends(verify_internal_api_key)])


def generate_auto_description(category: str, severity: float, confidence: float) -> str:
    """Generate structured description for the verified report."""
    severity_pct = int(severity * 100)
    conf_pct = int(confidence * 100)

    templates = {
        "Jalan Berlubang": f"Terdeteksi kerusakan permukaan aspal/jalan berlubang dengan estimasi keparahan {severity_pct}% (keyakinan AI {conf_pct}%). Memerlukan penambalan perkerasan jalan.",
        "Trotoar": f"Terdeteksi kerusakan jalur pejalan kaki/trotoar beton dengan estimasi keparahan {severity_pct}% (keyakinan AI {conf_pct}%). Memerlukan perbaikan struktur trotoar.",
        "Rambu Lalu Lintas": f"Terdeteksi kerusakan fisik atau anomali pada rambu lalu lintas dengan estimasi keparahan {severity_pct}% (keyakinan AI {conf_pct}%). Memerlukan peninjauan Dishub.",
        "Lampu Jalan": f"Terdeteksi gangguan penerangan jalan umum (PJU)/lampu rusak dengan estimasi keparahan {severity_pct}% (keyakinan AI {conf_pct}%). Memerlukan pengecekan instalasi.",
        "Drainase": f"Terdeteksi sumbatan atau kerusakan penutup saluran drainase dengan estimasi keparahan {severity_pct}% (keyakinan AI {conf_pct}%). Memerlukan pembersihan saluran air.",
        "bukan_fasilitas": "Citra teridentifikasi bukan merupakan kerusakan fasilitas publik (bukan_fasilitas).",
    }

    return templates.get(
        category,
        f"Terdeteksi kerusakan fasilitas umum kategori '{category}' dengan tingkat keparahan estimasi {severity_pct}% (keyakinan AI {conf_pct}%)."
    )


async def _run_verification(payload: VerifyReportRequest) -> dict:
    """
    Core verification pipeline (Rules.md §1.2 & FIX-1):
    1. Runs YOLOv11-cls image classification on the submitted photo.
    2. Validates GPS bounds against Kota Malang pilot area.
    3. Validates photo timestamp sanity.
    4. Applies verification decision:
       - confidence >= 0.6 AND GPS valid AND timestamp valid AND category != 'bukan_fasilitas' -> is_valid = True, needs_manual_review = False
       - confidence < 0.6 OR GPS/timestamp anomaly OR bukan_fasilitas -> is_valid = False, needs_manual_review = True
    Returns a dict of computed values; callers shape the response.
    """
    logger.info(f"AI Verification requested at ({payload.latitude}, {payload.longitude}), claimed='{payload.claimed_category}'")

    # 1. Validate GPS coordinates (Kota Malang Bounding Box)
    gps_is_valid = is_within_malang_bbox(payload.latitude, payload.longitude)

    # 2. Validate timestamp
    timestamp_is_valid, _ = validate_report_timestamp(payload.timestamp)

    # 3. Execute Real YOLOv11-cls inference asynchronously
    yolo_svc = YOLOClassificationService.get_instance()
    try:
        predicted_category, ai_confidence_score, class_probs, damage_severity = await asyncio.to_thread(
            yolo_svc.predict,
            image_url=payload.image_url,
            image_base64=payload.image_base64,
        )
    except ValueError as ve:
        raise ValueError(ve) from ve

    # 4. Verification Decision Rules (Rules.md §1.2 & FIX-1 OOD Guard)
    is_ood = predicted_category == "bukan_fasilitas"
    confidence_passed = (ai_confidence_score >= settings.AI_CONFIDENCE_THRESHOLD) and not is_ood
    is_valid = confidence_passed and gps_is_valid and timestamp_is_valid
    needs_manual_review = not is_valid

    # 5. Generate description & reasons
    if is_ood:
        description_auto = "Citra teridentifikasi bukan merupakan kerusakan fasilitas publik (bukan_fasilitas)."
        reason = "Perlu review manual: Citra terklasifikasi sebagai bukan fasilitas publik."
        damage_severity = 0.0
    else:
        description_auto = generate_auto_description(predicted_category, damage_severity, ai_confidence_score)
        reason = (
            "Lolos verifikasi otomatis (AI confidence >= threshold, GPS dan timestamp valid)"
            if is_valid
            else f"Perlu review manual: confidence={ai_confidence_score:.2f}, "
                 f"gps_valid={gps_is_valid}, timestamp_valid={timestamp_is_valid}"
        )

    return {
        "ai_confidence_score": ai_confidence_score,
        "predicted_category": predicted_category,
        "is_valid": is_valid,
        "needs_manual_review": needs_manual_review,
        "damage_severity": damage_severity,
        "description_auto": description_auto,
        "gps_valid": gps_is_valid,
        "timestamp_valid": timestamp_is_valid,
        "class_probs": class_probs,
        "reason": reason,
    }


@router.post(
    "",
    response_model=APIResponse[VerifyReportData],
    status_code=status.HTTP_200_OK,
    summary="Verify report image with YOLOv11 classification, validate GPS/timestamp, and calculate priority score"
)
async def verify_report(payload: VerifyReportRequest):
    """AI Verification endpoint (canonical, envelope response)."""
    try:
        result = await _run_verification(payload)
    except ValueError as ve:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=APIResponse[VerifyReportData](
                success=False,
                data=None,
                error=APIError(
                    code="INVALID_IMAGE",
                    message=str(ve),
                ),
            ).model_dump(by_alias=True),
        )
    except RuntimeError as re:
        logger.error(f"Verification service unavailable: {re}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=APIResponse[VerifyReportData](
                success=False,
                data=None,
                error=APIError(
                    code="MODEL_NOT_AVAILABLE",
                    message=str(re),
                ),
            ).model_dump(by_alias=True),
        )

    data = VerifyReportData(
        ai_confidence_score=result["ai_confidence_score"],
        predicted_category=result["predicted_category"],
        is_valid=result["is_valid"],
        needs_manual_review=result["needs_manual_review"],
        damage_severity=result["damage_severity"],
        description_auto=result["description_auto"],
        gps_valid=result["gps_valid"],
        timestamp_valid=result["timestamp_valid"],
        class_probabilities=result["class_probs"],
        is_placeholder=False,
    )

    return APIResponse(
        success=True,
        data=data,
        error=None,
    )


@verify_compat_router.post(
    "",
    response_model=VerifyReportNestJSData,
    status_code=status.HTTP_200_OK,
    summary="Verify report image (flat response for backend-laporkita / NestJS)",
)
async def verify_report_nestjs(payload: VerifyReportRequest):
    """Compatibility endpoint: flat response matching NestJS ai-verification.service.js expectations."""
    try:
        result = await _run_verification(payload)
    except ValueError as ve:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"error": str(ve)},
        )
    except RuntimeError as re:
        logger.error(f"Verification compat service unavailable: {re}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": str(re)},
        )

    return VerifyReportNestJSData(
        confidence=result["ai_confidence_score"],
        category=result["predicted_category"],
        is_valid_gps=result["gps_valid"],
        is_valid_timestamp=result["timestamp_valid"],
        damage_severity=result["damage_severity"],
        reason=result["reason"],
        is_mock=False,
    )
