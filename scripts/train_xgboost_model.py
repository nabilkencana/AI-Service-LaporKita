"""
Training Pipeline for LaporKita XGBoost Flood & Infrastructure Risk Model.
Uses synthetic historical zone metrics for demo purposes.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb

from scripts.generate_synthetic_zone_data import generate_synthetic_data, OUTPUT_CSV

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_OUTPUT_PATH = MODELS_DIR / "xgboost-flood-risk.json"
METRICS_OUTPUT_PATH = MODELS_DIR / "xgboost_metrics.json"

FEATURE_NAMES = [
    "rainfall_mm",
    "temperature_c",
    "report_density",
    "traffic_density",
    "drainage_issue_ratio",
    "monsoon_season",
]
TARGET_NAME = "flood_risk_probability"


def train_xgboost_model():
    print("=" * 60)
    print("LAPORKITA XGBOOST RISK PREDICTION MODEL TRAINING")
    print("=" * 60)

    # 1. Load or Generate Synthetic Dataset
    if not OUTPUT_CSV.exists():
        df = generate_synthetic_data(n_samples=6000)
    else:
        df = pd.read_csv(OUTPUT_CSV)
        print(f"Loaded existing synthetic dataset ({len(df)} samples) from {OUTPUT_CSV}")

    X = df[FEATURE_NAMES]
    y = df[TARGET_NAME]

    # 2. Train-Test Split (80% Train, 20% Test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )
    print(f"Dataset split: {len(X_train)} train samples, {len(X_test)} test samples.")

    # 3. Initialize & Train XGBoost Regressor
    model = xgb.XGBRegressor(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        objective="reg:squarederror",
        random_state=42,
        eval_metric="rmse",
    )

    print("Training XGBRegressor...")
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        verbose=False,
    )

    # 4. Evaluate on Test Set
    y_pred = model.predict(X_test)
    y_pred = np.clip(y_pred, 0.0, 1.0)

    r2 = r2_score(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae = mean_absolute_error(y_test, y_pred)

    print("\n" + "=" * 60)
    print("TEST SET EVALUATION RESULTS (SYNTHETIC DATA BASELINE)")
    print("=" * 60)
    print(f"R-squared (R2) Score : {r2:.4f}")
    print(f"Root Mean Sq Error   : {rmse:.4f}")
    print(f"Mean Absolute Error  : {mae:.4f}")

    # Feature Importances
    importances = model.feature_importances_
    feat_imp = {feat: round(float(imp), 4) for feat, imp in zip(FEATURE_NAMES, importances)}
    print("\nFeature Importances:")
    for feat, imp in sorted(feat_imp.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {feat:<22}: {imp:.4f}")

    # 5. Save Model Artifact to JSON
    model.save_model(str(MODEL_OUTPUT_PATH))
    print(f"\nSuccessfully saved XGBoost model to: {MODEL_OUTPUT_PATH.resolve()}")

    # 6. Save Metadata Metrics
    metrics = {
        "model_type": "XGBRegressor",
        "dataset_type": "SYNTHETIC_DEMO",
        "features": FEATURE_NAMES,
        "test_samples": len(X_test),
        "r2_score": round(float(r2), 4),
        "rmse": round(float(rmse), 4),
        "mae": round(float(mae), 4),
        "feature_importances": feat_imp,
        "disclaimer": "Trained on synthetic dataset for demo purposes. Requires retraining with authentic BMKG and DPUPR historical records before production deployment.",
    }

    with open(METRICS_OUTPUT_PATH, "w") as f:
        json.dump(metrics, f, indent=2)

    return model, metrics


if __name__ == "__main__":
    train_xgboost_model()
