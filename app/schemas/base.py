from typing import Generic, TypeVar, Optional, Any, Dict
from pydantic import BaseModel, Field

T = TypeVar("T")


class APIError(BaseModel):
    code: str = Field(..., description="Error code identifier (e.g. INVALID_COORDINATES, INFERENCE_ERROR)")
    message: str = Field(..., description="Human-readable error explanation")
    details: Optional[Any] = Field(default=None, description="Optional extra validation error details")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response envelope consistent with NestJS backend conventions (Rules.md §3)."""
    success: bool = Field(default=True, description="Indicates if operation was successful")
    data: Optional[T] = Field(default=None, description="Payload data returned on success")
    error: Optional[APIError] = Field(default=None, description="Error payload returned on failure")


class ModelsStatus(BaseModel):
    yolo_classification_loaded: bool = Field(..., description="Whether YOLOv11-cls model weights are loaded in memory")
    xgboost_risk_loaded: bool = Field(..., description="Whether XGBoost risk model weights are loaded in memory")
    llm_configured: bool = Field(default=True, description="Whether DeepSeek/LLM API key is configured")
    llm_connected: bool = Field(default=True, description="Whether DeepSeek/LLM API endpoint is reachable via live probe")
    gemini_configured: bool = Field(default=True, deprecated=True, description="Deprecated alias for LLM configuration status")


class HealthStatusData(BaseModel):
    status: str = Field(default="ok", description="Service health state")
    service: str = Field(default="ai-service", description="Service identifier")
    version: str = Field(default="1.0.0", description="Service version")
    environment: str = Field(default="development", description="Environment deployment stage")
    models: Optional[ModelsStatus] = Field(default=None, description="Operational readiness of ML models")
