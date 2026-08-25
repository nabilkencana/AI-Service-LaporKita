from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from fastapi.responses import JSONResponse, FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.schemas.base import APIResponse, APIError, HealthStatusData
from app.routers.verification import router as verification_router
from app.routers.verification import verify_compat_router
from app.routers.prediction import router as prediction_router
from app.routers.prediction import zone_metrics_router
from app.routers.policy_simulator import router as policy_simulator_router
from app.routers.active_learning import router as active_learning_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION} [{settings.APP_ENV}]")
    try:
        from app.services.yolo_service import YOLOClassificationService
        YOLOClassificationService.get_instance()
    except Exception as e:
        logger.warning(f"Could not preload YOLO model on startup: {e}")

    try:
        from app.services.xgboost_service import XGBoostRiskService
        XGBoostRiskService.get_instance()
    except Exception as e:
        logger.warning(f"Could not preload XGBoost model on startup: {e}")
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Microservice AI/ML LaporKita: Computer Vision Verification, Risk Prediction, and LLM Policy Simulator.",
    lifespan=lifespan,
    docs_url="/docs" if (settings.ENABLE_DOCS and settings.APP_ENV != "production") else None,
    redoc_url="/redoc" if (settings.ENABLE_DOCS and settings.APP_ENV != "production") else None,
    openapi_url="/openapi.json" if (settings.ENABLE_DOCS and settings.APP_ENV != "production") else None,
)

# Secure CORS Configuration (SEC-CORS Fix)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_CORS_ORIGINS,
    allow_credentials=False if "*" in settings.ALLOWED_CORS_ORIGINS else True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# Global Exception Handler for Request Validation Errors (Returns NestJS-compatible envelope)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    raw_errors = exc.errors()
    logger.warning(f"Validation error on {request.method} {request.url.path}: {raw_errors}")

    first_error = raw_errors[0] if raw_errors else {"msg": "Validation failed", "loc": []}
    loc = first_error.get("loc", ["field"])
    field_name = loc[-1] if loc else "field"
    error_msg = f"{field_name}: {first_error.get('msg', 'Invalid input')}"

    # Safely serialize error details using jsonable_encoder
    safe_details = jsonable_encoder(raw_errors)

    response_payload = APIResponse(
        success=False,
        data=None,
        error=APIError(
            code="VALIDATION_ERROR",
            message=error_msg,
            details=safe_details,
        ),
    )
    return JSONResponse(
        status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
        content=response_payload.model_dump(by_alias=True),
    )


# Global Exception Handler for HTTP Exceptions
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(f"HTTP exception on {request.method} {request.url.path} [{exc.status_code}]: {exc.detail}")
    response_payload = APIResponse(
        success=False,
        data=None,
        error=APIError(
            code=f"HTTP_{exc.status_code}",
            message=exc.detail,
        ),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=response_payload.model_dump(by_alias=True),
    )


# Global Exception Handler for Unhandled Exceptions
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    response_payload = APIResponse(
        success=False,
        data=None,
        error=APIError(
            code="INTERNAL_SERVER_ERROR",
            message="Terjadi kesalahan internal pada layanan AI.",
        ),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_payload.model_dump(by_alias=True),
    )


# Health check endpoint
@app.get(
    "/health",
    response_model=APIResponse[HealthStatusData],
    tags=["Health"],
    summary="Health check endpoint with ML models readiness verification"
)
async def health_check():
    """
    Returns service health status, environment, and operational readiness
    of ML models (YOLOv11-cls, XGBoost, and Gemini LLM).
    """
    from app.schemas.base import ModelsStatus
    from app.services.yolo_service import YOLOClassificationService
    from app.services.xgboost_service import XGBoostRiskService
    from app.services.deepseek_service import DeepSeekPolicyService

    yolo_svc = YOLOClassificationService.get_instance()
    xgb_svc = XGBoostRiskService.get_instance()
    llm_svc = DeepSeekPolicyService.get_instance()

    yolo_ready = yolo_svc.model is not None
    xgb_ready = xgb_svc.model is not None
    llm_configured = llm_svc.is_configured
    llm_connected = await llm_svc.check_connectivity() if llm_configured else False

    all_systems_ready = yolo_ready and xgb_ready and (llm_connected or not llm_configured)

    models_info = ModelsStatus(
        yolo_classification_loaded=yolo_ready,
        xgboost_risk_loaded=xgb_ready,
        llm_configured=llm_configured,
        llm_connected=llm_connected,
        gemini_configured=llm_configured,
    )

    return APIResponse(
        success=True,
        data=HealthStatusData(
            status="ok" if all_systems_ready else "degraded",
            service="ai-service",
            version=settings.VERSION,
            environment=settings.APP_ENV,
            models=models_info,
        ),
        error=None,
    )


# Include Routers under /v1 prefix
app.include_router(verification_router, prefix=settings.API_V1_STR)
app.include_router(prediction_router, prefix=settings.API_V1_STR)
app.include_router(zone_metrics_router, prefix=settings.API_V1_STR)
app.include_router(policy_simulator_router, prefix=settings.API_V1_STR)
app.include_router(active_learning_router, prefix=settings.API_V1_STR)

# /api/v1 mount: flat NestJS-compat handlers registered FIRST so they win over the
# canonical envelope handlers for the shared paths (e.g. /api/v1/verify).
app.include_router(verify_compat_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")
app.include_router(prediction_router, prefix="/api/v1")
app.include_router(zone_metrics_router, prefix="/api/v1")
app.include_router(policy_simulator_router, prefix="/api/v1")
app.include_router(active_learning_router, prefix="/api/v1")


from fastapi.responses import HTMLResponse

@app.get("/", include_in_schema=False)
@app.get("/demo", include_in_schema=False)
@app.get("/demo/", include_in_schema=False)
@app.get("/api/demo", include_in_schema=False)
async def serve_demo_console():
    """Serves the interactive web test console for manual QA & live model verification."""
    candidates = [
        Path("index.html"),
        Path(__file__).resolve().parent.parent / "index.html",
        Path(__file__).resolve().parent / "index.html",
        Path("/app/index.html"),
    ]
    for p in candidates:
        if p.exists():
            return FileResponse(str(p), media_type="text/html")
    return HTMLResponse(
        "<h2>LaporKita AI Service Online</h2><p>Visit <code>/health</code> for API status or <code>/docs</code> for Swagger UI.</p>"
    )


@app.get("/app/sample_images.json", include_in_schema=False)
@app.get("/sample_images.json", include_in_schema=False)
async def serve_sample_images():
    """Serves sample image presets for the demo web console."""
    candidates = [
        Path("app/sample_images.json"),
        Path(__file__).resolve().parent / "sample_images.json",
        Path("/app/app/sample_images.json"),
    ]
    for p in candidates:
        if p.exists():
            return FileResponse(str(p), media_type="application/json")
    return JSONResponse(status_code=404, content={"error": "sample_images.json not found"})

