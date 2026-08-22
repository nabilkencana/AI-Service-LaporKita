from fastapi import APIRouter, status
from app.schemas.base import APIResponse
from app.schemas.verification import VerifyReportRequest, VerifyReportData
from app.core.config import settings
from app.core.logging import logger
from app.services.yolo_service import YOLOClassificationService
from app.utils.gps_validator import is_within_malang_bbox, validate_report_timestamp
from app.utils.scoring import calculate_urgency_score

router = APIRouter(prefix="/verify", tags=["AI Verification"])


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
    }

    return templates.get(
        category,
        f"Terdeteksi kerusakan fasilitas umum kategori '{category}' dengan tingkat keparahan estimasi {severity_pct}% (keyakinan AI {conf_pct}%)."
    )


@router.post(
    "",
    response_model=APIResponse[VerifyReportData],
    status_code=status.HTTP_200_OK,
    summary="Verify report image with YOLOv11 classification, validate GPS/timestamp, and calculate priority score"
)
async def verify_report(payload: VerifyReportRequest):
    """
    AI Verification endpoint implementing Rules.md §1.2 & §1.3:
    1. Runs YOLOv11-cls image classification on the submitted photo.
    2. Validates GPS bounds against Kota Malang pilot area.
    3. Validates photo timestamp sanity.
    4. Applies verification decision:
       - confidence >= 0.6 AND GPS valid AND timestamp valid -> is_valid = True, needs_manual_review = False
       - confidence < 0.6 OR GPS/timestamp anomaly -> is_valid = False, needs_manual_review = True (manual review queue)
    5. Calculates Smart Priority urgency score.
    """
    logger.info(f"AI Verification requested at ({payload.latitude}, {payload.longitude}), claimed='{payload.claimed_category}'")

    # 1. Validate GPS coordinates (Kota Malang Bounding Box)
    gps_is_valid = is_within_malang_bbox(payload.latitude, payload.longitude)

    # 2. Validate timestamp
    timestamp_is_valid, _ = validate_report_timestamp(payload.timestamp)

    # 3. Execute Real YOLOv11-cls inference
    yolo_svc = YOLOClassificationService.get_instance()
    predicted_category, ai_confidence_score, class_probs, damage_severity = yolo_svc.predict(
        image_url=payload.image_url,
        image_base64=payload.image_base64,
    )

    # 4. Verification Decision Rules (Rules.md §1.2):
    # - ai_confidence_score >= 0.6 -> lolos otomatis, KECUALI jika ada anomali GPS/timestamp
    # - ai_confidence_score < 0.6 -> otomatis masuk antrian verifikasi manual (needs_manual_review = True)
    confidence_passed = ai_confidence_score >= settings.AI_CONFIDENCE_THRESHOLD
    is_valid = confidence_passed and gps_is_valid and timestamp_is_valid
    needs_manual_review = not is_valid

    # 5. Calculate Smart Priority urgency score (Rules.md §1.3)
    urgency_score = calculate_urgency_score(
        damage_severity=damage_severity,
        support_count=0,
        report_density=5,
        category_name=predicted_category,
    )

    # 6. Generate description
    description_auto = generate_auto_description(predicted_category, damage_severity, ai_confidence_score)

    data = VerifyReportData(
        ai_confidence_score=ai_confidence_score,
        predicted_category=predicted_category,
        is_valid=is_valid,
        needs_manual_review=needs_manual_review,
        damage_severity=damage_severity,
        urgency_score=urgency_score,
        description_auto=description_auto,
        gps_valid=gps_is_valid,
        timestamp_valid=timestamp_is_valid,
        class_probabilities=class_probs,
        is_placeholder=False,
    )

    return APIResponse(
        success=True,
        data=data,
        error=None,
    )
