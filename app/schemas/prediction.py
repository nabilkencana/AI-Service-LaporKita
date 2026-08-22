from typing import Optional, Dict
from pydantic import BaseModel, Field, ConfigDict


class WeatherContext(BaseModel):
    rainfall_mm: float = Field(default=0.0, ge=0.0, description="Rainfall in millimeters over last period")
    temperature_c: float = Field(default=27.0, description="Ambient temperature in Celsius")
    condition: Optional[str] = Field(default="Berawan", description="Text description of weather (e.g. Hujan Lebat, Cerah)")
    drainage_issue_ratio: Optional[float] = Field(default=0.2, ge=0.0, le=1.0, description="Ratio of drainage complaints")


class PredictRiskRequest(BaseModel):
    zone_id: Optional[str] = Field(default=None, description="UUID of urban zone (ERD.md §2.11)")
    report_density: int = Field(default=0, ge=0, description="Aggregated report count in the zone/area")
    weather_context: Optional[WeatherContext] = Field(default_factory=WeatherContext, description="Meteorological conditions")
    traffic_density: Optional[float] = Field(default=0.5, ge=0.0, le=1.0, description="Normalized traffic congestion level (0.0 to 1.0)")
    category: Optional[str] = Field(default="Drainase", description="Target facility category for risk estimation")


class PredictRiskData(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    flood_risk_probability: float = Field(..., ge=0.0, le=1.0, description="Calculated probability of flood/risk (0.0 to 1.0)")
    risk_level: str = Field(..., description="Categorized risk: low, medium, high")
    predicted_stress_level: str = Field(..., description="Urban stress classification: low, medium, high (ERD.md §2.11)")
    factors: Dict[str, float] = Field(default_factory=dict, description="Factor contribution breakdown to the risk score")
    recommendation: str = Field(..., description="Actionable recommendation for DPUPR/Dishub")
    is_placeholder: bool = Field(default=False, alias="_placeholder", serialization_alias="_placeholder", description="Indicates whether response is placeholder (False for real trained XGBoost model)")
