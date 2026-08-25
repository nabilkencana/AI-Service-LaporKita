import asyncio
from fastapi import APIRouter, status, Depends, HTTPException
from app.schemas.base import APIResponse, APIError
from app.schemas.active_learning import (
    IngestSampleRequest,
    IngestSampleData,
    DatasetStatsData,
)
from app.core.logging import logger
from app.core.security import verify_internal_api_key
from app.services.active_learning_service import ActiveLearningService

router = APIRouter(prefix="/training", tags=["Active Learning & MLOps"], dependencies=[Depends(verify_internal_api_key)])


@router.post(
    "/ingest-sample",
    response_model=APIResponse[IngestSampleData],
    status_code=status.HTTP_201_CREATED,
    summary="Ingest verified citizen report photo into Active Learning continuous training dataset"
)
async def ingest_training_sample(payload: IngestSampleRequest):
    """
    Ingests human-verified ground-truth photos into the categorized training pool.
    Called when an operator marks a report as 'resolved' or updates its category.
    """
    service = ActiveLearningService.get_instance()
    try:
        result = await asyncio.to_thread(
            service.ingest_sample,
            image_base64=payload.image_base64,
            image_url=payload.image_url,
            verified_category=payload.verified_category,
            original_prediction=payload.original_prediction,
            confidence_score=payload.confidence_score,
            report_id=payload.report_id,
            operator_notes=payload.operator_notes,
            source=payload.source,
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(ve)) from ve
    except Exception as e:
        logger.error(f"Failed to ingest training sample: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Gagal mengarsipkan sampel: {e}") from e

    data = IngestSampleData(
        saved_file=result["saved_file"],
        target_category=result["target_category"],
        is_correction=result["is_correction"],
        total_samples_in_class=result["total_samples_in_class"],
    )

    return APIResponse(
        success=True,
        data=data,
        error=None,
    )


@router.get(
    "/dataset-stats",
    response_model=APIResponse[DatasetStatsData],
    status_code=status.HTTP_200_OK,
    summary="Get statistics and class distribution of the Active Learning dataset"
)
async def get_dataset_stats():
    """
    Returns real-time distribution of gathered training samples across categories.
    """
    service = ActiveLearningService.get_instance()
    stats = await asyncio.to_thread(service.get_dataset_statistics)

    data = DatasetStatsData(
        total_samples=stats["total_samples"],
        corrections_from_human_operators=stats["corrections_from_human_operators"],
        class_distribution=stats["class_distribution"],
        dataset_directory=stats["dataset_directory"],
        ready_for_retraining=stats["ready_for_retraining"],
    )

    return APIResponse(
        success=True,
        data=data,
        error=None,
    )


from fastapi.responses import StreamingResponse, FileResponse
from pathlib import Path

@router.get(
    "/download-dataset",
    summary="Download the entire gathered Active Learning dataset as a ZIP archive"
)
async def download_dataset_zip():
    """
    Downloads all ingested training images and JSONL metadata packaged in a .zip file.
    """
    service = ActiveLearningService.get_instance()
    zip_buffer = await asyncio.to_thread(service.create_dataset_zip)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=laporkita_active_learning_dataset.zip"}
    )


@router.get(
    "/samples/{class_name}/{filename}",
    summary="View or download an individual training image sample"
)
async def get_training_sample_image(class_name: str, filename: str):
    """
    Serves the image file for viewing in browser.
    """
    service = ActiveLearningService.get_instance()
    file_path = service.labeled_dir / class_name / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File gambar tidak ditemukan")
    return FileResponse(file_path, media_type="image/jpeg")
