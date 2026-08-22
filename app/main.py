from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.schemas.base import APIResponse, APIError, HealthStatusData
from app.routers.verification import router as verification_router
from app.routers.prediction import router as prediction_router
from app.routers.policy_simulator import router as policy_simulator_router


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
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
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
            message=str(exc.detail),
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
    summary="Health check endpoint"
)
async def health_check():
    """Returns service health status and active version."""
    return APIResponse(
        success=True,
        data=HealthStatusData(
            status="ok",
            service="ai-service",
            version=settings.VERSION,
            environment=settings.APP_ENV,
        ),
        error=None,
    )


# Include Routers under /v1 prefix
app.include_router(verification_router, prefix=settings.API_V1_STR)
app.include_router(prediction_router, prefix=settings.API_V1_STR)
app.include_router(policy_simulator_router, prefix=settings.API_V1_STR)
