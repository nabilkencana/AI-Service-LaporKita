"""
========================================================================================
XGBoost Risk Prediction Service for LaporKita
========================================================================================
DISCLAIMER SINTETIS (Rules.md & Bagian 0 Decision #4):
Model XGBoost ini dilatih menggunakan dataset hidrologi & lalu lintas SINTETIS untuk
keperluan demonstrasi baseline arsitektur AI Service LaporKita.
Sebelum implementasi production, model WAJIB di-retrain dengan data observasi asli dari
BMKG Weather API dan riwayat laporan penanganan fisik DPUPR Kota Malang.
========================================================================================
"""

from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
import xgboost as xgb

from app.core.config import settings
from app.core.logging import logger


class XGBoostRiskService:
    _instance: Optional["XGBoostRiskService"] = None

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or settings.XGBOOST_MODEL_PATH
        self.model: Optional[xgb.XGBRegressor] = None
        self._load_model()

    @classmethod
    def get_instance(cls) -> "XGBoostRiskService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_model(self):
        """Load trained XGBoost model from JSON artifact once."""
        path = Path(self.model_path)
        if not path.exists():
            base_dir = Path(__file__).resolve().parent.parent.parent
            alt_path = base_dir / self.model_path
            if alt_path.exists():
                path = alt_path

        if path.exists():
            try:
                logger.info(f"Loading XGBoost risk model from {path.resolve()}...")
                self.model = xgb.XGBRegressor()
                self.model.load_model(str(path.resolve()))
                logger.info("XGBoost risk model successfully loaded into memory.")
            except Exception as e:
                logger.error(f"Failed to load XGBoost model from {path}: {e}")
                self.model = None
        else:
            logger.warning(f"XGBoost model file not found at {path}. Running in fallback heuristic mode.")
            self.model = None

    def predict_risk(
        self,
        report_density: int = 0,
        rainfall_mm: float = 0.0,
        temperature_c: float = 27.0,
        traffic_density: float = 0.5,
        drainage_issue_ratio: float = 0.2,
        monsoon_season: Optional[int] = None,
    ) -> Tuple[float, str, str, Dict[str, float], str]:
        """
        Predict flood & infrastructure failure risk probability.
        
        Returns:
            (flood_risk_probability, risk_level, predicted_stress_level, factors, recommendation)
        """
        # Infer monsoon season if not explicitly passed
        if monsoon_season is None:
            monsoon_season = 1 if rainfall_mm >= 25.0 else 0

        # Construct feature vector
        feature_dict = {
            "rainfall_mm": [float(rainfall_mm)],
            "temperature_c": [float(temperature_c)],
            "report_density": [int(report_density)],
            "traffic_density": [float(traffic_density)],
            "drainage_issue_ratio": [float(drainage_issue_ratio)],
            "monsoon_season": [int(monsoon_season)],
        }
        df_feat = pd.DataFrame(feature_dict)

        if self.model is None:
            logger.error("XGBoost model is not loaded in memory")
            raise RuntimeError("Model prediksi risiko XGBoost tidak tersedia atau gagal dimuat")

        try:
            pred_prob = float(self.model.predict(df_feat)[0])
            flood_risk_prob = round(float(np.clip(pred_prob, 0.01, 0.99)), 4)
        except Exception as e:
            logger.error(f"Inference error with XGBoost model: {e}")
            raise RuntimeError(f"Gagal melakukan inferensi model XGBoost: {e}") from e

        # 1. Determine Risk Level (ERD.md §2.12)
        if flood_risk_prob >= 0.70:
            risk_level = "high"
        elif flood_risk_prob >= 0.40:
            risk_level = "medium"
        else:
            risk_level = "low"

        # 2. Determine Urban Stress Level (ERD.md §2.11)
        stress_score = (flood_risk_prob * 0.6) + (traffic_density * 0.4)
        if stress_score >= 0.65:
            stress_level = "high"
        elif stress_score >= 0.35:
            stress_level = "medium"
        else:
            stress_level = "low"

        # 3. Factor Contribution Breakdown
        factors = {
            "rainfall_impact": round(min(1.0, rainfall_mm / 100.0), 3),
            "report_density_impact": round(min(1.0, report_density / 40.0), 3),
            "traffic_congestion_impact": round(traffic_density, 3),
            "drainage_vulnerability_impact": round(drainage_issue_ratio, 3),
        }

        # 4. Actionable Recommendation
        recommendation = self._generate_recommendation(risk_level, stress_level, rainfall_mm, report_density)

        return flood_risk_prob, risk_level, stress_level, factors, recommendation

    def _heuristic_fallback(self, rainfall: float, density: int, traffic: float) -> float:
        """Deterministic mathematical proxy fallback."""
        score = (rainfall * 0.005) + (density * 0.015) + (traffic * 0.3)
        return round(float(np.clip(score, 0.05, 0.95)), 4)

    def _generate_recommendation(self, risk: str, stress: str, rain: float, density: int) -> str:
        """Generate structured recommendation for city agencies."""
        if risk == "high":
            return (
                f"STATUS WASPADA: Probabilitas genangan tinggi terdeteksi (Curah hujan: {rain:.1f} mm, {density} laporan aktif). "
                "Direkomendasikan pengerahan pompa bergerak DPUPR dan pengalihan rute lalu lintas oleh Dishub."
            )
        elif risk == "medium":
            return (
                f"STATUS SIAGA: Zona memiliki beban infrastruktur menengah ({density} laporan). "
                "Perlu inspeksi rutin saringan drainase dan pemantauan titik genangan air."
            )
        else:
            return (
                "STATUS AMAN: Risiko genangan dan stres wilayah berada dalam batas toleransi normal. "
                "Tetap laksanakan pemeliharaan terjadwal berkala."
            )
