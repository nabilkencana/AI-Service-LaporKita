# LaporKita — AI Service Microservice

Microservice Python FastAPI untuk platform **LaporKita**, menyediakan inference Computer Vision (klasifikasi kerusakan fasilitas), prediksi risiko berbasis Machine Learning (XGBoost), dan Policy Simulator berbasis LLM (Gemini 2.5).

Service ini dipanggil secara internal oleh Backend Gateway NestJS (`Architecture.md §3.2`).

---

## ⚠️ Limitasi Eksplisit & Catatan Demo

1. **Dataset Publik (Bukan Foto Asli Malang):** Seluruh model klasifikasi gambar YOLOv11 dilatih dan dievaluasi menggunakan **dataset publik** (5 kelas fasilitas). Belum ada sesi validasi dengan foto lapangan kondisi nyata Kota Malang pada demo ini. Metrik akurasi yang dilaporkan (99.49%) berlaku untuk test set dataset publik.
2. **Data Historis Sintetis (XGBoost):** Data historis cuaca, traffic, dan densitas laporan untuk model XGBoost menggunakan **dataset sintetis terkalibrasi hidrologi perkotaan** (`scripts/generate_synthetic_zone_data.py`).
3. **Kebutuhan Retraining Produksi:** Sebelum implementasi operasional nyata di Kota Malang, model XGBoost **WAJIB di-retrain** menggunakan data observasi historis resmi (stasiun cuaca BMKG Karangploso/Malang dan riwayat laporan penanganan fisik DPUPR Kota Malang).

---

## 🚀 Panduan Menjalankan

### 1. Menjalankan secara Lokal (Virtual Environment)

**Prasyarat:** Python 3.11+

```bash
# 1. Buat dan aktifkan virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup environment variables
cp .env.example .env

# 4. Jalankan unit test (16 test cases)
pytest -v

# 5. Jalankan server FastAPI
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Dokumentasi OpenAPI/Swagger UI otomatis tersedia di: `http://localhost:8000/docs`

---

### 2. Pipeline Training Model ML

#### A. Training Model Klasifikasi YOLOv11-cls (Fase 3)
```bash
python scripts/train_yolo_classifier.py
```
- **Bobot model:** `models/yolov11-cls-laporkita.pt`
- **Laporan evaluasi:** [`training_report.md`](file:///Users/nabilkencana/Project%20/Lomba%20MAGEITS/ai-service/training_report.md)

#### B. Training Model Prediksi Risiko XGBoost (Fase 4)
```bash
python scripts/train_xgboost_model.py
```
- **Dataset sintetis:** `dataset_staging/synthetic_zone_metrics.csv` (6.000 sampel)
- **Bobot model:** `models/xgboost-flood-risk.json`
- **Metrik evaluasi:** $R^2 = 0.9635$, $\text{RMSE} = 0.0490$, $\text{MAE} = 0.0369$

---

### 3. Menjalankan dengan Docker

```bash
# Build image
docker build -t laporkita-ai-service:1.0.0 .

# Jalankan container
docker run -d -p 8000:8000 --name laporkita-ai-service laporkita-ai-service:1.0.0

# Atau menggunakan Docker Compose
docker compose up -d
```

---

## 📡 Kontrak API & Endpoints

Seluruh endpoint mengembalikan format response envelope standar sesuai konvensi backend NestJS (`Rules.md §3`):

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

Jika terjadi kesalahan (error/validasi):
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Deskripsi kesalahan",
    "details": [ ... ]
  }
}
```

### Daftar Endpoint

| Method | Endpoint | Deskripsi | Status Implementasi |
|---|---|---|---|
| `GET` | `/health` | Health check & versi service | ✅ Selesai |
| `POST` | `/v1/verify` | AI Verification klasifikasi gambar (YOLOv11-cls), validasi GPS/timestamp, dan Smart Priority | ✅ **Model Aktif (YOLOv11-cls)** |
| `POST` | `/v1/predict-risk` | Prediksi probabilitas risiko genangan & infrastruktur (XGBoost) | ✅ **Model Aktif (XGBoost)** |
| `POST` | `/v1/policy-simulate` | Simulasi kebijakan perkotaan & proyeksi dampak (Gemini) | 🟡 Kontrak Aktif (Fase 5) |

---

## 📊 Struktur Data Sintetis XGBoost (ERD.md §2.12)

Dataset sintetis (`dataset_staging/synthetic_zone_metrics.csv`) dibuat dengan formula hidrologi perkotaan logistik:

| Fitur | Tipe | Rentang Nilai | Deskripsi & Rasional Domain |
|---|---|---|---|
| `rainfall_mm` | float | 0.0 – 140.0 mm | Curah hujan harian (simulasi BMKG musim hujan vs kemarau) |
| `temperature_c` | float | 18.0 – 35.0 °C | Suhu udara ambien (°C) |
| `report_density` | int | 0 – 60 | Jumlah laporan aktif di zona wilayah |
| `traffic_density` | float | 0.05 – 0.98 | Tingkat kemacetan lalu lintas (0.0=lancar, 1.0=macet total) |
| `drainage_issue_ratio`| float | 0.0 – 1.0 | Rasio laporan yang berkaitan dengan saluran drainase tersumbat |
| `monsoon_season` | int | 0 / 1 | Indikator musim penghujan di Jawa Timur/Malang |
| **`flood_risk_probability`** | float | 0.01 – 0.99 | **Target Prediksi:** Probabilitas genangan/kerusakan infrastruktur |
| **`risk_level`** | string | low, medium, high | Kategori risiko: `low` (<0.40), `medium` (0.40–0.70), `high` (≥0.70) |

---

## 🧪 Pengujian (Unit Test)

Jalankan test suite menggunakan pytest:

```bash
pytest -v
```

Hasil test (16 test cases) mencakup:
- Validasi status kesehatan (`GET /health`)
- Uji inferensi YOLOv11 pada seluruh 5 kelas fasilitas umum
- Uji aturan verifikasi otomatis (threshold $\ge 0.6$ vs $< 0.6$, anomali GPS di luar Malang, dan anomali timestamp)
- Uji inferensi XGBoost (sanity check: curah hujan tinggi & densitas tinggi menghasilkan probabilitas risiko lebih tinggi dibanding input rendah)
- Uji rumus Smart Priority urgency scoring
- Uji serialisasi format error envelope untuk input invalid (422)
