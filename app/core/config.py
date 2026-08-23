from typing import List, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Information
    APP_NAME: str = "LaporKita AI Service"
    APP_ENV: str = "development"
    VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # API Prefix
    API_V1_STR: str = "/v1"

    # AI Verification Thresholds (Rules.md §1.2)
    # ai_confidence_score < 0.6 -> needs_manual_review = True
    AI_CONFIDENCE_THRESHOLD: float = 0.6

    # Kota Malang Bounding Box Coordinates (Rules.md §2.1)
    MALANG_BBOX_MIN_LAT: float = -8.0500
    MALANG_BBOX_MAX_LAT: float = -7.9000
    MALANG_BBOX_MIN_LON: float = 112.5500
    MALANG_BBOX_MAX_LON: float = 112.7000

    # Smart Priority Weights (Rules.md §1.3)
    # urgency_score = (w1 * damage_severity) + (w2 * support_count_normalized)
    #               + (w3 * location_density_factor) + (w4 * category_urgency_weight)
    WEIGHT_DAMAGE_SEVERITY: float = 0.35
    WEIGHT_SUPPORT_COUNT: float = 0.25
    WEIGHT_LOCATION_DENSITY: float = 0.20
    WEIGHT_CATEGORY_URGENCY: float = 0.20

    # 5 Active Facility Categories (PRD & Rules.md) + OOD Class
    VALID_CATEGORIES: List[str] = [
        "Jalan Berlubang",
        "Lampu Jalan",
        "Rambu Lalu Lintas",
        "Trotoar",
        "Drainase",
        "bukan_fasilitas",
    ]

    # Category Urgency Default Weights (0.0 to 1.0)
    DEFAULT_CATEGORY_WEIGHTS: Dict[str, float] = {
        "Jalan Berlubang": 0.9,
        "Drainase": 0.85,
        "Rambu Lalu Lintas": 0.8,
        "Lampu Jalan": 0.7,
        "Trotoar": 0.65,
        "bukan_fasilitas": 0.0,
    }

    # Internal API Authentication (SEC-NOAUTH fix)
    INTERNAL_API_KEY: str = ""

    # External Model / API Keys
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"

    # DeepSeek API (for Policy Simulator Migration)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL_NAME: str = "deepseek-chat"

    # Security & Resource Constraints (Rules.md §2.1 & Empirical Distribution Calibrated)
    MAX_IMAGE_SIZE_BYTES: int = 8 * 1024 * 1024  # 8 MB
    MAX_IMAGE_PIXELS: int = 16_000_000            # Max 16 Megapixels
    MIN_IMAGE_DIMENSION: int = 200                # Min 200px longest edge (calibrated for benchmark crops >=200px)
    ALLOWED_CORS_ORIGINS: List[str] = ["*"]
    ENABLE_DOCS: bool = True

    # Model file paths (Phases 3-5)
    CLASSIFICATION_MODEL_PATH: str = "models/yolov11-cls-laporkita.pt"
    XGBOOST_MODEL_PATH: str = "models/xgboost-flood-risk.json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
