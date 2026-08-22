from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field, ConfigDict, model_validator


class VerifyReportRequest(BaseModel):
    image_url: Optional[str] = Field(default=None, description="Public / pre-signed URL of the report image")
    image_base64: Optional[str] = Field(default=None, description="Base64-encoded image string if URL is not provided")
    claimed_category: Optional[str] = Field(default=None, description="Category selected by user")
    latitude: float = Field(..., description="GPS Latitude of report location")
    longitude: float = Field(..., description="GPS Longitude of report location")
    timestamp: Optional[datetime] = Field(default=None, description="Capture timestamp of photo/report")
    device_hint_category: Optional[str] = Field(default=None, description="On-device classification hint")
    device_hint_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="On-device confidence score")

    @model_validator(mode="before")
    @classmethod
    def normalize_nestjs_fields(cls, data):
        """Accept NestJS backend-laporkita field names as aliases."""
        if isinstance(data, dict):
            if data.get("photo_url") and not data.get("image_url"):
                data = {**data, "image_url": data["photo_url"]}
            if data.get("reported_category") and not data.get("claimed_category"):
                data = {**data, "claimed_category": data["reported_category"]}
            if data.get("created_at") and not data.get("timestamp"):
                data = {**data, "timestamp": data["created_at"]}
        return data

    @model_validator(mode="after")
    def check_image_present(self):
        if not self.image_url and not self.image_base64:
            raise ValueError("Either image_url or image_base64 must be provided")
        return self


class VerifyReportData(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    ai_confidence_score: float = Field(..., ge=0.0, le=1.0, description="Model classification confidence score (0.0 to 1.0)")
    predicted_category: str = Field(..., description="Classification category determined by model")
    is_valid: bool = Field(..., description="Whether report is automatically verified (confidence >= threshold and GPS/timestamp valid)")
    needs_manual_review: bool = Field(..., description="True if confidence < 0.6 or GPS/timestamp anomaly (Rules.md §1.2)")
    damage_severity: float = Field(..., ge=0.0, le=1.0, description="Estimated damage severity score (0.0 to 1.0)")
    urgency_score: float = Field(..., ge=0.0, le=1.0, description="Calculated Smart Priority urgency score")
    description_auto: str = Field(..., description="Auto-generated descriptive text for the report")
    gps_valid: bool = Field(..., description="Whether GPS coordinates are inside Malang City bounds")
    timestamp_valid: bool = Field(..., description="Whether report timestamp is recent and valid")
    class_probabilities: Optional[Dict[str, float]] = Field(default_factory=dict, description="Softmax confidence distribution across all 5 classes")
    is_placeholder: bool = Field(default=False, alias="_placeholder", serialization_alias="_placeholder", description="Indicates whether response is placeholder (False for real YOLOv11 model)")


class VerifyReportNestJSData(BaseModel):
    """Flat response shape expected by backend-laporkita (NestJS) ai-verification.service.js."""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    confidence: float = Field(..., ge=0.0, le=1.0, description="Model classification confidence score (0.0 to 1.0)")
    category: str = Field(..., description="Classification category determined by model")
    is_valid_gps: bool = Field(..., description="Whether GPS coordinates are inside Malang City bounds")
    is_valid_timestamp: bool = Field(..., description="Whether report timestamp is recent and valid")
    damage_severity: float = Field(..., ge=0.0, le=1.0, description="Estimated damage severity score (0.0 to 1.0)")
    reason: str = Field(..., description="Human-readable verification decision reason")
    is_mock: bool = Field(default=False, description="False for real YOLOv11 model inference")
