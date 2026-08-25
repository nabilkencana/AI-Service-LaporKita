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
    def check_inputs(self):
        if not self.image_url and not self.image_base64:
            raise ValueError("Either image_url or image_base64 must be provided")
        if self.claimed_category is not None:
            from app.core.config import settings
            if self.claimed_category not in settings.VALID_CATEGORIES:
                raise ValueError(
                    f"Kategori '{self.claimed_category}' tidak valid. Harus salah satu dari: {', '.join(settings.VALID_CATEGORIES)}"
                )
        return self


class AuthenticitySnapshot(BaseModel):
    is_authentic: bool = Field(default=True, description="True if image has no AI tampering or inpainting detected")
    authenticity_score: float = Field(default=0.95, ge=0.0, le=1.0, description="Image authenticity confidence score (0.0 to 1.0)")
    tampering_detected: bool = Field(default=False, description="True if ELA or noise anomaly indicates AI inpainting/tampering")
    tampering_indicators: list[str] = Field(default_factory=list, description="List of detected digital anomalies")
    assessment_summary: str = Field(default="Citra terverifikasi otentik", description="Summary of digital forensics analysis")


class LocationVerificationSnapshot(BaseModel):
    is_location_consistent: bool = Field(default=True, description="True if coordinates match physical road landscape")
    location_match_confidence: float = Field(default=0.90, ge=0.0, le=1.0, description="Confidence of visual/geospatial location match")
    verified_address: str = Field(default="Kota Malang, Jawa Timur", description="Resolved street/district address")
    district_name: str = Field(default="Kota Malang", description="Malang municipal district name")
    street_view_available: bool = Field(default=True, description="Whether Google Street View reference exists")
    location_audit_notes: str = Field(default="", description="Notes from spatial cross-verification")


class VerifyReportData(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    ai_confidence_score: float = Field(..., ge=0.0, le=1.0, description="Model classification confidence score (0.0 to 1.0)")
    predicted_category: str = Field(..., description="Classification category determined by model")
    is_valid: bool = Field(..., description="Whether report is automatically verified (confidence >= threshold and GPS/timestamp valid)")
    needs_manual_review: bool = Field(..., description="True if confidence < 0.6 or GPS/timestamp anomaly or bukan_fasilitas (Rules.md §1.2)")
    damage_severity: float = Field(..., ge=0.0, le=1.0, description="Estimated damage severity score (0.0 to 1.0)")
    description_auto: str = Field(..., description="Auto-generated descriptive text for the report")
    gps_valid: bool = Field(..., description="Whether GPS coordinates are inside Malang City bounds")
    timestamp_valid: bool = Field(..., description="Whether report timestamp is recent and valid")
    class_probabilities: Optional[Dict[str, float]] = Field(default_factory=dict, description="Softmax confidence distribution across all classes")
    authenticity: Optional[AuthenticitySnapshot] = Field(default_factory=AuthenticitySnapshot, description="Digital tampering & AI inpainting forensics")
    location_verification: Optional[LocationVerificationSnapshot] = Field(default_factory=LocationVerificationSnapshot, description="Google Maps & Street View location cross-check")
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
    is_authentic: bool = Field(default=True, description="True if no digital tampering/AI inpainting detected")
    verified_address: Optional[str] = Field(default=None, description="Resolved physical street address in Malang")
    is_mock: bool = Field(default=False, description="False for real YOLOv11 model inference")
