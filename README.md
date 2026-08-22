# LaporKita — AI Service Microservice

Microservice Python FastAPI mandiri untuk platform **LaporKita**, menyediakan inference Computer Vision (klasifikasi kerusakan fasilitas publik), prediksi risiko wilayah berbasis Machine Learning (XGBoost), dan Policy Simulator interaktif berbasis LLM (Google Gemini 2.5 Flash).

Service ini berkomunikasi secara internal dengan Backend Gateway NestJS (`Architecture.md §3.2`) melalui protokol REST JSON standar.

---

## 📑 Daftar Isi
1. [Arsitektur & Fitur Utama](#-arsitektur--fitur-utama)
2. [Panduan Menjalankan](#-panduan-menjalankan)
   - [A. Menjalankan secara Lokal (.venv)](#a-menjalankan-secara-lokal-venv)
   - [B. Menjalankan dengan Docker & Docker Compose](#b-menjalankan-dengan-docker--docker-compose)
   - [C. Verifikasi Clean-State (Zero-State Test)](#c-verifikasi-clean-state-zero-state-test)
3. [Daftar Lengkap Environment Variables](#-daftar-lengkap-environment-variables)
4. [Dokumentasi Endpoint & Contoh Request/Response](#-dokumentasi-endpoint--contoh-requestresponse)
   - [1. GET /health](#1-get-health)
   - [2. POST /v1/verify](#2-post-v1verify)
   - [3. POST /v1/predict-risk](#3-post-v1predict-risk)
   - [4. POST /v1/policy-simulate](#4-post-v1policy-simulate)
5. [Ringkasan Dataset Publik (5 Kategori)](#-ringkasan-dataset-publik-5-kategori)
6. [Metrik Evaluasi Model Riil](#-metrik-evaluasi-model-riil)
   - [A. YOLOv11-cls Computer Vision (Test Set: 390 Citra)](#a-yolov11-cls-computer-vision-test-set-390-citra)
   - [B. XGBoost Risk Prediction (Test Set: 1.200 Sampel)](#b-xgboost-risk-prediction-test-set-1200-sampel)
7. [⚠️ Batasan & Known Limitations untuk Produksi](#️-batasan--known-limitations-untuk-produksi)

---

## 🏛️ Arsitektur & Fitur Utama

```
                      +-----------------------------+
                      |   LaporKita NestJS Gateway  |
                      +--------------+--------------+
                                     |
                       Internal REST | (Rules.md §3)
                                     v
+------------------------------------------------------------------------+
|                     FastAPI AI Microservice (:8000)                    |
|                                                                        |
|  +--------------------+  +--------------------+  +-------------------+ |
|  |  AI Verification   |  |   Risk Prediction  |  |  Policy Simulator | |
|  |    (YOLOv11-cls)   |  |      (XGBoost)     |  |   (Gemini 2.5)    | |
|  +---------+----------+  +---------+----------+  +---------+---------+ |
|            |                       |                       |           |
|            v                       v                       v           |
|   models/yolov11-cls-     models/xgboost-        Google Gemini 2.5     |
|       laporkita.pt        flood-risk.json              Flash           |
+------------------------------------------------------------------------+
```

1. **AI Verification (`POST /v1/verify`):** Klasifikasi gambar 5 kelas fasilitas publik (*Jalan Berlubang, Trotoar, Rambu Lalu Lintas, Lampu Jalan, Drainase*), validasi koordinat Bounding Box Kota Malang, deteksi anomali timestamp, dan perhitungan skor urgensi *Smart Priority* (`Rules.md §1.2 - §1.3`).
2. **Urban Risk Prediction (`POST /v1/predict-risk`):** Estimasi probabilitas risiko genangan air dan tingkat stres wilayah (*low, medium, high*) berdasarkan kepadatan laporan, curah hujan, dan kepadatan lalu lintas (`ERD.md §2.12`).
3. **Policy Simulator (`POST /v1/policy-simulate`):** Simulasi skenario intervensi kebijakan publik oleh Bappeda/DPUPR/Dishub dengan proyeksi anggaran, reduksi insiden, durasi waktu, dan rekomendasi strategis (`PRD.md §4.2`).

---

## 🚀 Panduan Menjalankan

### A. Menjalankan secara Lokal (.venv)

**Prasyarat:** Python 3.11+

```bash
# 1. Clone & masuk ke direktori service
git clone https://github.com/nabilkencana/AI-Service-LaporKita.git
cd AI-Service-LaporKita

# 2. Buat dan aktifkan virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Install seluruh dependensi
pip install --upgrade pip
pip install -r requirements.txt

# 4. Salin file konfigurasi environment
cp .env.example .env

# 5. Jalankan unit test suite (21 unit test)
pytest -v

# 6. Jalankan server FastAPI
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Dokumentasi interaktif OpenAPI/Swagger UI otomatis tersedia di: **`http://localhost:8000/docs`**

---

### B. Menjalankan dengan Docker & Docker Compose

Proyek menggunakan Dockerfile multi-stage yang ringan dengan model weights yang disalin langsung ke dalam container (*self-contained*):

```bash
# Menggunakan Docker Compose (Recommended)
docker compose up --build -d

# Cek log aplikasi
docker compose logs -f ai-service

# Stop container
docker compose down
```

---

### C. Verifikasi Clean-State (Zero-State Test)

Untuk memastikan aplikasi berjalan mandiri tanpa state lokal yang tertinggal:

```bash
# 1. Bersihkan seluruh container dan volume lama
docker compose down -v

# 2. Build ulang dari nol dan jalankan
docker compose up --build -d

# 3. Verifikasi kesiapan layanan & model
curl -s http://localhost:8000/health | json_pp

# 4. Jalankan skrip pengujian live
python scripts/test_live_verification.py
python scripts/test_live_gemini_policy.py
```

---

## ⚙️ Daftar Lengkap Environment Variables

Konfigurasi dimuat melalui Pydantic Settings dari file `.env`:

| Variabel | Tipe | Default | Deskripsi |
|---|---|---|---|
| `APP_NAME` | string | `LaporKita AI Service` | Nama aplikasi service |
| `APP_ENV` | string | `development` | Environment (`development` / `production`) |
| `PORT` | int | `8000` | Port listen server |
| `HOST` | string | `0.0.0.0` | Host listen server |
| `LOG_LEVEL` | string | `INFO` | Tingkat logging (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `AI_CONFIDENCE_THRESHOLD` | float | `0.6` | Ambang batas minimum kelolosan otomatis verifikasi AI (`Rules.md §1.2`) |
| `MALANG_BBOX_MIN_LAT` | float | `-8.0500` | Batas selatan Bounding Box Kota Malang |
| `MALANG_BBOX_MAX_LAT` | float | `-7.9000` | Batas utara Bounding Box Kota Malang |
| `MALANG_BBOX_MIN_LON` | float | `112.5500` | Batas barat Bounding Box Kota Malang |
| `MALANG_BBOX_MAX_LON` | float | `112.7000` | Batas timur Bounding Box Kota Malang |
| `WEIGHT_DAMAGE_SEVERITY` | float | `0.35` | Bobot keparahan kerusakan pada Smart Priority (`Rules.md §1.3`) |
| `WEIGHT_SUPPORT_COUNT` | float | `0.25` | Bobot dukungan/upvote warga pada Smart Priority |
| `WEIGHT_LOCATION_DENSITY` | float | `0.20` | Bobot kepadatan laporan wilayah pada Smart Priority |
| `WEIGHT_CATEGORY_URGENCY` | float | `0.20` | Bobot urgensi kategori fasilitas pada Smart Priority |
| `CLASSIFICATION_MODEL_PATH` | string | `models/yolov11-cls-laporkita.pt` | Path file bobot model klasifikasi YOLOv11 |
| `XGBOOST_MODEL_PATH` | string | `models/xgboost-flood-risk.json` | Path file bobot model risiko XGBoost |
| `GEMINI_API_KEY` | string | `""` | API Key Google Gemini 2.5 Flash |
| `GEMINI_MODEL_NAME` | string | `gemini-2.5-flash` | Identifier model Gemini yang digunakan |

---

## 📡 Dokumentasi Endpoint & Contoh Request/Response

Seluruh endpoint mengikuti format response envelope standar sesuai `Rules.md §3`:
```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

---

### 1. `GET /health`
Mengecek status kesehatan server serta kesiapan operasional model ML di memori.

#### Response (HTTP 200 OK):
```json
{
  "success": true,
  "data": {
    "status": "ok",
    "service": "ai-service",
    "version": "1.0.0",
    "environment": "development",
    "models": {
      "yolo_classification_loaded": true,
      "xgboost_risk_loaded": true,
      "gemini_configured": true
    }
  },
  "error": null
}
```

---

### 2. `POST /v1/verify`
Melakukan verifikasi otomatis terhadap laporan foto warga:
- Jika $\text{Confidence} \ge 0.6$ dan GPS/Timestamp Valid $\rightarrow$ `is_valid: true, needs_manual_review: false`.
- Jika $\text{Confidence} < 0.6$ atau GPS/Timestamp Anomali $\rightarrow$ `is_valid: false, needs_manual_review: true` (masuk antrean review manual operator, **bukan ditolak**).

#### Request Example:
```json
{
  "image_base64": "/9j/4AAQSkZJRgABAQAAAQABAAD...",
  "claimed_category": "Jalan Berlubang",
  "latitude": -7.9826,
  "longitude": 112.6308,
  "timestamp": "2026-08-23T02:00:00Z"
}
```

#### Response Example (HTTP 200 OK):
```json
{
  "success": true,
  "data": {
    "ai_confidence_score": 1.0,
    "predicted_category": "Jalan Berlubang",
    "is_valid": true,
    "needs_manual_review": false,
    "damage_severity": 0.96,
    "urgency_score": 0.536,
    "description_auto": "Terdeteksi kerusakan permukaan aspal/jalan berlubang dengan estimasi keparahan 96% (keyakinan AI 100%). Memerlukan penambalan perkerasan jalan.",
    "gps_valid": true,
    "timestamp_valid": true,
    "class_probabilities": {
      "Drainase": 0.0,
      "Jalan Berlubang": 1.0,
      "Lampu Jalan": 0.0,
      "Rambu Lalu Lintas": 0.0,
      "Trotoar": 0.0
    },
    "_placeholder": false
  },
  "error": null
}
```

---

### 3. `POST /v1/predict-risk`
Memprediksi probabilitas risiko genangan air dan tingkat stres wilayah (*low, medium, high*) berdasarkan data cuaca BMKG dan beban infrastruktur.

#### Request Example:
```json
{
  "zone_id": "zone-klojen-01",
  "report_density": 25,
  "weather_context": {
    "rainfall_mm": 65.0,
    "temperature_c": 23.5,
    "condition": "Hujan Lebat",
    "drainage_issue_ratio": 0.45
  },
  "traffic_density": 0.8
}
```

#### Response Example (HTTP 200 OK):
```json
{
  "success": true,
  "data": {
    "flood_risk_probability": 0.8421,
    "risk_level": "high",
    "predicted_stress_level": "high",
    "factors": {
      "rainfall_impact": 0.65,
      "report_density_impact": 0.625,
      "traffic_congestion_impact": 0.8,
      "drainage_vulnerability_impact": 0.45
    },
    "recommendation": "STATUS WASPADA: Probabilitas genangan tinggi terdeteksi (Curah hujan: 65.0 mm, 25 laporan aktif). Direkomendasikan pengerahan pompa bergerak DPUPR dan pengalihan rute lalu lintas oleh Dishub.",
    "_placeholder": false
  },
  "error": null
}
```

---

### 4. `POST /v1/policy-simulate`
Mensimulasikan skenario kebijakan pemerintah kota menggunakan LLM Google Gemini 2.5 Flash dengan validasi skema JSON terstruktur.

#### Request Example:
```json
{
  "prompt_text": "Bagaimana proyeksi dampak jika Pemkot Malang mengalokasikan anggaran Rp 1.5 Miliar untuk normalisasi gorong-gorong di sepanjang koridor Jalan Soekarno-Hatta menjelang musim hujan?",
  "zone_id": "zone-lowokwaru-suhat",
  "time_horizon_months": 6,
  "parameters": {
    "allocated_budget_idr": 1500000000,
    "target_district": "Lowokwaru"
  }
}
```

#### Response Example (HTTP 200 OK):
```json
{
  "success": true,
  "data": {
    "result_narrative": "Koridor Jalan Soekarno-Hatta di Kecamatan Lowokwaru merupakan salah satu arteri vital Kota Malang yang sering mengalami permasalahan genangan air saat musim hujan...",
    "result_data": {
      "estimated_incident_reduction_pct": 65.0,
      "budget_estimate_idr": 1500000000.0,
      "time_to_impact_weeks": 10,
      "target_department": "Dinas Pekerjaan Umum, Penataan Ruang, Perumahan dan Kawasan Permukiman (DPUPRPKP) Kota Malang",
      "public_satisfaction_increase_pct": 45.0,
      "risk_mitigations": [
        "Manajemen lalu lintas dan sosialisasi rute alternatif selama pengerjaan.",
        "Penanganan dan pembuangan sedimen hasil pengerukan sesuai standar lingkungan."
      ]
    },
    "key_recommendations": [
      "Melakukan monitoring dan evaluasi berkala terhadap kinerja drainase pasca-normalisasi.",
      "Menggalakkan program edukasi pengelolaan sampah agar tidak membuang ke saluran air.",
      "Mengintegrasikan data curah hujan dan sistem peringatan dini banjir."
    ],
    "model_used": "gemini-2.5-flash",
    "_placeholder": false
  },
  "error": null
}
```

---

## 📊 Ringkasan Dataset Publik (5 Kategori)

Rincian lengkap dan URL verifikasi didokumentasikan di [`dataset_report.md`](file:///Users/nabilkencana/Project%20/Lomba%20MAGEITS/ai-service/dataset_report.md):

| Kategori LaporKita | Nama Dataset Publik | Sumber / URL Publik | Lisensi | Total Clean | Train (70%) | Val (15%) | Test (15%) |
|---|---|---|---|---|---|---|---|
| **Jalan Berlubang** | Roboflow Pothole / RDD2022 subset | [HuggingFace: keremberke/pothole-segmentation](https://huggingface.co/datasets/keremberke/pothole-segmentation) | CC BY 4.0 | **486** | 340 | 72 | 74 |
| **Trotoar** | METU Concrete Crack Images (CCIC) | [Mendeley Data: 10.17632/5y9wdsg2zt.2](https://data.mendeley.com/datasets/5y9wdsg2zt/2) | CC BY 4.0 | **600** | 420 | 90 | 90 |
| **Rambu Lalu Lintas** | German Traffic Sign Detection (GTSDB) | [HuggingFace: keremberke/german-traffic-sign-detection](https://huggingface.co/datasets/keremberke/german-traffic-sign-detection) | CC BY 4.0 | **491** | 343 | 73 | 75 |
| **Lampu Jalan** | Team16 Street Light Dataset | [GitHub: Team16Project/Street-Light-Dataset](https://github.com/Team16Project/Street-Light-Dataset) | MIT | **447** | 312 | 67 | 68 |
| **Drainase** | Manhole Covers & Storm Drains | [HuggingFace: delima87/manhole_covers_dataset](https://huggingface.co/datasets/delima87/manhole_covers_dataset) | CC BY 4.0 | **545** | 381 | 81 | 83 |
| **TOTAL** | | | | **2.569** | **1.796** | **383** | **390** |

---

## 📈 Metrik Evaluasi Model Riil

### A. YOLOv11-cls Computer Vision (Test Set: 390 Citra)
*Evaluasi riil pada held-out test set independen (`dataset/test/`):*

- **Top-1 Accuracy Global:** **99.49%** (388 / 390 citra terklasifikasi benar)
- **Macro Average F1-Score:** **99.48%**
- **Kecepatan Inferensi:** **~2.1 ms per citra** (MPS GPU)

| Kategori Fasilitas | Precision | Recall | F1-Score | Support (Sampel Uji) |
|---|---|---|---|---|
| **Drainase** | 0.9880 | 0.9880 | **0.9880** | 83 |
| **Jalan Berlubang** | 1.0000 | 0.9865 | **0.9932** | 74 |
| **Lampu Jalan** | 0.9855 | 1.0000 | **0.9927** | 68 |
| **Rambu Lalu Lintas** | 1.0000 | 1.0000 | **1.0000** | 75 |
| **Trotoar** | 1.0000 | 1.0000 | **1.0000** | 90 |

*Laporan evaluasi mendalam tersedia di [`training_report.md`](file:///Users/nabilkencana/Project%20/Lomba%20MAGEITS/ai-service/training_report.md).*

---

### B. XGBoost Risk Prediction (Test Set: 1.200 Sampel)
*Evaluasi pada dataset sintetis hidrologi perkotaan:*
- **$R^2$ Score:** **0.9635**
- **RMSE:** **0.0490**
- **MAE:** **0.0369** (Rata-rata deviasi probabilitas ±3.69%)

---

## ⚠️ Batasan & Known Limitations untuk Produksi

Untuk keterbukaan teknis (*technical honesty*), berikut adalah batasan sistem pada versi demo saat ini:

1. **Domain Shift & Zero Malang Field Validation:** Model YOLOv11 dilatih pada dataset publik standar internasional. Belum dilakukan validasi dengan foto lapangan warga Kota Malang. Performa dapat terpengaruh oleh sudut pengambilan gambar warga, kamera beresolusi rendah, atau variasi pencahayaan ekstrem.
2. **Kategori Proxy Visual:**
   - *Trotoar:* Menggunakan citra retak pelat beton (*concrete cracks*) sebagai proxy kerusakan permukaan jalan kaki — belum mencakup variasi paving block lokal.
   - *Drainase:* Menggunakan citra grill saluran air dan manhole cover jalan — belum sepenuhnya mencakup parit/selokan tanah terbuka di permukiman padat.
   - *Rambu Lalu Lintas:* Berbasis rambu standar Eropa (GTSDB) yang memiliki perbedaan piktogram minor dibanding rambu Dishub Indonesia.
3. **Data Historis XGBoost Sintetis:** Model XGBoost dilatih pada dataset sintetis berbasis simulasi hidrologi logistik (`scripts/generate_synthetic_zone_data.py`). **WAJIB di-retrain** dengan deret waktu curah hujan stasiun BMKG Karangploso dan log penanganan fisik DPUPR Kota Malang sebelum digunakan untuk pengambilan kebijakan anggaran riil.
4. **Metrik `damage_severity` sebagai Proxy:** Model bekerja dalam mode klasifikasi citra per kategori, sehingga `damage_severity` merupakan estimasi terkalibrasi dari confidence model dan bobot urgensi kelas, bukan pengukuran langsung luas fisik kerusakan per meter persegi.
