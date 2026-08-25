from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class IngestSampleRequest(BaseModel):
    image_base64: Optional[str] = Field(default=None, description="Base64 encoded photo")
    image_url: Optional[str] = Field(default=None, description="Image URL if stored in cloud")
    verified_category: str = Field(..., description="Ground truth category confirmed by operator or field action")
    original_prediction: Optional[str] = Field(default=None, description="Initial category predicted by YOLO model")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Initial confidence score of AI prediction")
    report_id: Optional[str] = Field(default=None, description="UUID of the report in LaporKita database")
    operator_notes: Optional[str] = Field(default=None, description="Notes from field survey or resolution")
    source: str = Field(default="operator_action", description="Source of verification (e.g. operator_action, survey, citizen_consensus)")


class IngestSampleData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    saved_file: str = Field(..., description="Generated image filename in dataset")
    target_category: str = Field(..., description="Category folder where sample was archived")
    is_correction: bool = Field(..., description="True if operator corrected an initial misclassification by AI")
    total_samples_in_class: int = Field(..., description="Current count of samples in this class")


class DatasetStatsData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_samples: int = Field(..., description="Total training samples collected")
    corrections_from_human_operators: int = Field(..., description="Count of samples where humans corrected AI errors")
    class_distribution: Dict[str, int] = Field(..., description="Sample count breakdown per class")
    dataset_directory: str = Field(..., description="Storage directory path")
    ready_for_retraining: bool = Field(..., description="Whether enough samples have been gathered for a fine-tuning run")
