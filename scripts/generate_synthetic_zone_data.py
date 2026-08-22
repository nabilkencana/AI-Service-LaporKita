"""
========================================================================================
LAPORKITA SYNTHETIC ZONE METRICS GENERATOR (DEMO ONLY)
========================================================================================
PERINGATAN PENTING & DISCLAIMER DATA:
Dataset yang dihasilkan oleh script ini adalah DATA SINTETIS untuk keperluan demo & baseline
Machine Learning (XGBoost) LaporKita, karena data historis sensor cuaca BMKG dan riwayat
laporan lapangan DPUPR/Dishub Kota Malang belum tersedia dalam format terbuka.

ATURAN BISNIS & FORMULA DOMAIN:
Fitur-fitur disesuaikan dengan skema ERD.md §2.12 (zone_metrics):
- report_density: akumulasi laporan kerusakan/sumbatan di zona (0-50 laporan)
- rainfall_mm: curah hujan harian dari stasiun cuaca (0-120 mm/hari)
- temperature_c: suhu udara ambien (18-35 °C)
- traffic_density: kepadatan lalu lintas jalan utama (0.0 - 1.0)
- drainage_issue_ratio: rasio laporan khusus saluran air/drainase tersumbat (0.0 - 1.0)
- monsoon_season: indikator musim penghujan di Malang (1=Nov-Maret, 0=April-Okt)

Target:
- flood_risk_probability: probabilitas genangan/banjir (0.0 - 1.0) dihitung secara rasional
  melalui fungsi logistik hidrologi perkotaan + gaussian noise terkontrol.

CATATAN PRODUKSI:
Sistem WAJIB di-retrain dengan data observasi riil (BMKG Weather API + data laporan DPUPR)
sebelum digunakan dalam operasional kebijakan pemerintah sesungguhnya.
========================================================================================
"""

import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "dataset_staging"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_CSV = OUTPUT_DIR / "synthetic_zone_metrics.csv"

np.random.seed(42)


def generate_synthetic_data(n_samples: int = 6000) -> pd.DataFrame:
    print(f"[DATA GENERATOR] Generating {n_samples} synthetic zone metric samples...")

    # 1. Simulate Monsoon Season (50% probability across year)
    monsoon_season = np.random.choice([0, 1], size=n_samples, p=[0.5, 0.5])

    # 2. Simulate Rainfall (mm) - higher during monsoon
    rainfall_mm = np.where(
        monsoon_season == 1,
        np.random.gamma(shape=3.5, scale=12.0, size=n_samples),   # mean ~42mm, max ~120mm
        np.random.gamma(shape=1.5, scale=5.0, size=n_samples)     # mean ~7.5mm, dry season
    )
    rainfall_mm = np.clip(rainfall_mm, 0.0, 140.0)

    # 3. Simulate Temperature (Celsius)
    temperature_c = 28.0 - (rainfall_mm * 0.05) + np.random.normal(0, 1.5, size=n_samples)
    temperature_c = np.clip(temperature_c, 18.0, 35.0)

    # 4. Simulate Report Density (number of active reports in zone)
    # Higher rainfall slightly increases structural failure & reports
    base_density = np.random.poisson(lam=10.0, size=n_samples)
    density_boost = (rainfall_mm * 0.15).astype(int)
    report_density = np.clip(base_density + density_boost, 0, 60)

    # 5. Simulate Traffic Density (0.0 to 1.0)
    # Rain increases congestion
    traffic_density = np.random.beta(a=2.0, b=2.0, size=n_samples) + (rainfall_mm * 0.002)
    traffic_density = np.clip(traffic_density, 0.05, 0.98)

    # 6. Simulate Drainage Issue Ratio (0.0 to 1.0)
    drainage_issue_ratio = np.random.beta(a=1.5, b=3.0, size=n_samples)
    drainage_issue_ratio = np.clip(drainage_issue_ratio, 0.0, 1.0)

    # 7. Hydrological Domain Rule for Flood Risk Probability
    # z = w_rain * rain + w_rep * report + w_traf * traffic + w_drain * drainage_ratio + noise
    z_score = (
        (0.040 * rainfall_mm)
        + (0.050 * report_density)
        + (0.850 * traffic_density)
        + (1.400 * drainage_issue_ratio)
        + (0.400 * monsoon_season)
        - 3.200  # bias threshold
        + np.random.normal(0, 0.25, size=n_samples)  # stochastic environmental noise
    )

    # Logistic Sigmoid Transformation
    flood_risk_prob = 1.0 / (1.0 + np.exp(-z_score))
    flood_risk_prob = np.clip(flood_risk_prob, 0.01, 0.99)

    # Categorize Risk Level (Rules.md alignment)
    risk_level = np.where(flood_risk_prob >= 0.70, "high", np.where(flood_risk_prob >= 0.40, "medium", "low"))

    df = pd.DataFrame({
        "rainfall_mm": np.round(rainfall_mm, 2),
        "temperature_c": np.round(temperature_c, 1),
        "report_density": report_density,
        "traffic_density": np.round(traffic_density, 3),
        "drainage_issue_ratio": np.round(drainage_issue_ratio, 3),
        "monsoon_season": monsoon_season,
        "flood_risk_probability": np.round(flood_risk_prob, 4),
        "risk_level": risk_level,
        "is_synthetic": True,
    })

    print("[DATA GENERATOR] Generation complete. Sample statistics:")
    print(df[["rainfall_mm", "report_density", "traffic_density", "flood_risk_probability"]].describe())
    print("\nRisk Level Distribution:")
    print(df["risk_level"].value_counts(normalize=True))

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\n[DATA GENERATOR] Saved synthetic dataset to: {OUTPUT_CSV.resolve()}")
    return df


if __name__ == "__main__":
    generate_synthetic_data(n_samples=6000)
