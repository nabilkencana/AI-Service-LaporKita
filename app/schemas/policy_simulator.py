from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class PolicySimulateRequest(BaseModel):
    prompt_text: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Policy question or scenario proposed by policy maker (ERD.md §2.13)"
    )
    zone_id: Optional[str] = Field(default=None, description="Target zone UUID if simulation is localized")
    time_horizon_months: Optional[int] = Field(default=6, ge=1, le=60, description="Simulation duration in months")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional contextual parameters (budget, workforce, intervention type)")


class PolicyProjectionData(BaseModel):
    estimated_incident_reduction_pct: float = Field(default=0.0, ge=0.0, le=100.0, description="Estimated percentage drop in complaints/incidents")
    budget_estimate_idr: Optional[float] = Field(default=0.0, ge=0.0, description="Estimated budget in IDR")
    time_to_impact_weeks: Optional[int] = Field(default=4, ge=1, le=52, description="Weeks until visible public impact (1 to 52 weeks)")
    target_department: Optional[str] = Field(default="DPUPRPKP Kota Malang", description="Primary executing agency")
    public_satisfaction_increase_pct: Optional[float] = Field(default=0.0, ge=0.0, le=100.0, description="Projected satisfaction gain")
    risk_mitigations: List[str] = Field(default_factory=list, description="Key operational risk mitigations")


class PolicySimulateData(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    result_narrative: str = Field(..., description="In-depth narrative analysis and simulated outcome")
    result_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Projected figures and statistics (e.g. estimated_incident_reduction_pct, budget_allocation_idr)"
    )
    key_recommendations: List[str] = Field(
        default_factory=list,
        description="Actionable policy steps for city departments"
    )
    model_used: str = Field(default="deepseek-chat", description="LLM model identifier used for generation")
    is_placeholder: bool = Field(default=False, alias="_placeholder", serialization_alias="_placeholder", description="Indicates whether response is placeholder (False for real DeepSeek response)")
