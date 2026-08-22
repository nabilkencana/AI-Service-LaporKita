from datetime import datetime
from typing import Optional
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
    is_placeholder: bool = Field(default=True, alias="_placeholder", serialization_alias="_placeholder", description="Indicates placeholder/mock implementation for Phase 1")
