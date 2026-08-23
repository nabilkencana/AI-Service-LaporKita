# 🤖 LaporKita — AI Service

<div align="center">

**Microservice Python FastAPI mandiri untuk platform LaporKita — platform pelaporan kerusakan infrastruktur publik Kota Malang berbasis AI.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![YOLOv11](https://img.shields.io/badge/YOLOv11--cls-99.49%25_Acc-FF6F00?style=for-the-badge&logo=opencv&logoColor=white)](https://ultralytics.com)
[![XGBoost](https://img.shields.io/badge/XGBoost-R²%3D0.9635-4CAF50?style=for-the-badge)](https://xgboost.readthedocs.io)
[![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![Docker](https://img.shields.io/badge/Docker-Self--Contained-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)

</div>

> **Microservice Python FastAPI** mandiri untuk platform **LaporKita** — platform pelaporan kerusakan infrastruktur publik Kota Malang berbasis AI.

Service ini menyediakan tiga kapabilitas AI/ML utama:
1. **AI Verification** — Klasifikasi gambar 5 kelas kerusakan fasilitas publik menggunakan Computer Vision (YOLOv11-cls)
2. **Urban Risk Prediction** — Estimasi probabilitas risiko banjir dan stres wilayah menggunakan Machine Learning (XGBoost)
3. **Policy Simulator** — Proyeksi dampak kebijakan pemerintah kota menggunakan LLM (Google Gemini 2.5 Flash)

---

## 📑 Daftar Isi

- [Arsitektur & Infrastruktur](#️-arsitektur--infrastruktur)
- [Struktur Direktori Proyek](#-struktur-direktori-proyek)
- [Cara Menjalankan Lokal](#-cara-menjalankan-lokal-venv)
- [Cara Menjalankan dengan Docker](#-cara-menjalankan-dengan-docker)
- [Daftar Lengkap Environment Variables](#️-daftar-lengkap-environment-variables)
- [Routing & URL Mapping (Dual-Prefix)](#-routing--url-mapping-dual-prefix)
- [Dokumentasi Lengkap Semua Endpoint](#-dokumentasi-lengkap-semua-endpoint)
  - [GET /health](#1-get-health)
  - [POST /v1/verify — Canonical (envelope)](#2-post-v1verify--canonical-envelope)
  - [POST /api/v1/verify — NestJS Compat (flat)](#3-post-apiv1verify--nestjs-compat-flat)
  - [POST /v1/predict-risk](#4-post-v1predict-risk)
  - [POST /v1/predict/zone-metrics — NestJS Compat](#5-post-v1predictzoneметрики--nestjs-compat)
  - [POST /v1/policy-simulate](#6-post-v1policy-simulate)
- [Format Response Envelope Standar](#-format-response-envelope-standar)
- [Error Codes & HTTP Status Reference](#-error-codes--http-status-reference)
- [Ringkasan Dataset Publik](#-ringkasan-dataset-publik-5-kategori)
- [Metrik Evaluasi Model Riil](#-metrik-evaluasi-model-riil)
- [Arsitektur Decision Log](#-arsitektur-decision-log)
- [⚠️ Disclaimer & Known Limitations](#️-disclaimer--known-limitations-produksi)

---

## 🏛️ Arsitektur & Infrastruktur

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   LaporKita — Citizen Reporting Platform                │
│                                                                         │
│   Mobile App (Flutter)  ──►  Backend Gateway (NestJS :3000)            │
│                                        │                               │
│                              Internal REST HTTP                         │
│                                        │                               │
│                                        ▼                               │
│             ┌──────────────────────────────────────────┐               │
│             │       AI Microservice  (FastAPI :8000)   │               │
│             │                                          │               │
│             │  ┌────────────┐  ┌──────────────────┐   │               │
│             │  │ /v1/verify │  │/v1/predict-risk  │   │               │
│             │  │ /api/v1/   │  │/v1/predict/      │   │               │
│             │  │  verify    │  │  zone-metrics    │   │               │
│             │  └─────┬──────┘  └────────┬─────────┘   │               │
│             │        │                  │              │               │
│             │  ┌─────▼──────┐  ┌────────▼─────────┐   │               │
│             │  │  YOLOv11   │  │  XGBoost Regr.  │   │               │
│             │  │  -cls nano │  │  flood-risk.json │   │               │
│             │  │  (2.1 ms)  │  │  (R²=0.9635)    │   │               │
│             │  └────────────┘  └──────────────────┘   │               │
│             │                                          │               │
│             │  ┌──────────────────────────────────┐   │               │
│             │  │     /v1/policy-simulate          │   │               │
│             │  │  Gemini 2.5 Flash + Structured  │   │               │
│             │  │  JSON Pydantic Validation        │   │               │
│             │  └──────────────────────────────────┘   │               │
│             └──────────────────────────────────────────┘               │
│                                                                         │
│   Infrastructure: Docker · PostgreSQL (PostGIS) · Redis · Minio        │
└─────────────────────────────────────────────────────────────────────────┘
```

### Teknologi Stack

| Layer | Teknologi | Versi | Peran |
|---|---|---|---|
| Web Framework | FastAPI | `>=0.110.0` | ASGI routing, Pydantic validation, OpenAPI docs |
| ASGI Server | Uvicorn | `>=0.28.0` | Production ASGI server with uvloop |
| Computer Vision | Ultralytics YOLOv11 | `>=8.3.0` | Image classification (5-class, `-cls` mode) |
| ML Baseline | XGBoost | `>=2.0.0` | Risk regression (`XGBRegressor`) |
| LLM | Google Gemini 2.5 Flash | via `google-genai>=1.0.0` | Structured JSON policy simulation |
| Image Processing | Pillow | `>=10.0.0` | Base64 decode, URL fetch, YOLO pre-processing |
| Data Processing | Pandas + NumPy | `>=2.0.0 / >=1.24.0` | XGBoost feature matrix |
| Validation | Pydantic v2 | `>=2.6.0` | Schema + settings validation |
| Config | Pydantic Settings | `>=2.2.0` | Environment variables from `.env` |
| Containerization | Docker + Compose | - | Self-contained deployment |

---

## 📁 Struktur Direktori Proyek

```
ai-service/
├── app/
│   ├── core/
│   │   ├── config.py               # Pydantic Settings — semua env variable
│   │   └── logging.py              # Logging setup (structlog / stdlib)
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── verification.py         # /v1/verify (canonical) + /api/v1/verify (NestJS compat)
│   │   ├── prediction.py           # /v1/predict-risk + /v1/predict/zone-metrics
│   │   └── policy_simulator.py     # /v1/policy-simulate
│   ├── schemas/
│   │   ├── base.py                 # APIResponse[T], APIError, HealthStatusData, ModelsStatus
│   │   ├── verification.py         # VerifyReportRequest, VerifyReportData, VerifyReportNestJSData
│   │   ├── prediction.py           # PredictRiskRequest/Data, PredictZoneMetricsRequest/Data
│   │   └── policy_simulator.py     # PolicySimulateRequest, PolicySimulateData, PolicyProjectionData
│   ├── services/
│   │   ├── yolo_service.py         # Singleton YOLOv11 classifier (lazy-loaded at startup)
│   │   ├── xgboost_service.py      # Singleton XGBoost risk predictor
│   │   └── gemini_service.py       # Gemini 2.5 Flash with 20s timeout + Pydantic validation
│   ├── utils/
│   │   ├── gps_validator.py        # Malang bbox check + timestamp anomaly detection
│   │   └── scoring.py              # Smart Priority urgency score calculation
│   └── main.py                     # FastAPI app, lifespan, global error handlers, router mounting
├── models/
│   ├── yolov11-cls-laporkita.pt    # Trained YOLOv11-cls model weights (5 classes)
│   └── xgboost-flood-risk.json     # Trained XGBoost regressor weights
├── scripts/
│   ├── download_datasets.py        # Fase 2: dataset acquisition dari sumber publik
│   ├── prepare_dataset.py          # Fase 2: cleaning, stratified 70/15/15 split
│   ├── train_yolo_classifier.py    # Fase 3: training YOLOv11-cls + confusion matrix
│   ├── generate_synthetic_zone_data.py  # Fase 4: synthetic dataset 6.000 sampel hidrologi
│   ├── train_xgboost_model.py      # Fase 4: training XGBoost + evaluasi
│   ├── test_live_verification.py   # Fase 6: live E2E test semua 5 kelas
│   └── test_live_gemini_policy.py  # Fase 6: live E2E test Gemini API
├── tests/
│   ├── test_health.py              # Health check + model readiness verification
│   ├── test_verification.py        # 6 test cases: 5 kelas, GPS anomali, timestamp, corrupt image
│   ├── test_prediction.py          # 3 test cases: stress rendah/tinggi, invalid input
│   ├── test_policy_simulator.py    # 4 test cases: sukses, malformed JSON, timeout, validasi input
│   └── test_utils.py               # 7 test cases: GPS bbox, timestamp edge cases, scoring formula
├── dataset/
│   ├── train/                      # 1.796 gambar (70%), dibagi per kelas
│   ├── val/                        # 383 gambar (15%), dibagi per kelas
│   └── test/                       # 390 gambar (15%), dibagi per kelas
├── dataset_report.md               # Dokumentasi lengkap sumber dataset, lisensi, distribusi
├── training_report.md              # Metrik evaluasi riil YOLOv11 (99.49% test set accuracy)
├── Dockerfile                      # Single-stage, CPU PyTorch, model weights di-copy ke image
├── docker-compose.yml              # Stack orchestration + env injection
├── requirements.txt                # Pinned dependencies
├── pytest.ini                      # pytest asyncio configuration
├── .env.example                    # Template environment variables
└── README.md
```

---

## 🚀 Cara Menjalankan Lokal (.venv)

**Prasyarat:** Python 3.11+, Git

```bash
# 1. Clone repository
git clone https://github.com/nabilkencana/AI-Service-LaporKita.git
cd AI-Service-LaporKita

# 2. Buat virtual environment
python3.11 -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows

# 3. Install dependensi
pip install --upgrade pip
pip install -r requirements.txt

# 4. Buat file .env dari template
cp .env.example .env
# Edit .env dan isi GEMINI_API_KEY dengan API key Anda

# 5. Jalankan unit test (21 tests, seharusnya semua pass)
pytest -v

# 6. Jalankan server FastAPI
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

> **⚠️ Perhatian:** Gunakan `app.main:app` (bukan `main:app`). Service memerlukan model weights
> di `models/yolov11-cls-laporkita.pt` dan `models/xgboost-flood-risk.json`.

Setelah server aktif, buka:
- **Swagger UI (Interaktif):** `http://localhost:8000/docs`
- **ReDoc (Dokumentasi):** `http://localhost:8000/redoc`
- **OpenAPI JSON Schema:** `http://localhost:8000/openapi.json`

---

## 🐳 Cara Menjalankan dengan Docker

Service dikemas sebagai container mandiri (*self-contained*) — model weights sudah ter-copy ke dalam image saat `docker build`.

### Menggunakan Docker Compose (Rekomendasi)

```bash
# Jalankan di background
docker compose up -d

# Lihat log real-time
docker compose logs -f ai-service

# Hentikan service
docker compose down
```

### Build & Run Manual

```bash
# Build image
docker build -t laporkita-ai-service:1.0.0 .

# Jalankan container
docker run -d \
  --name laporkita-ai-service \
  -p 8000:8000 \
  -e GEMINI_API_KEY=your_api_key_here \
  laporkita-ai-service:1.0.0
```

### Verifikasi Clean-State (Zero-State Test)

```bash
# 1. Bersihkan semua state lama
docker compose down -v

# 2. Build dan jalankan ulang dari nol
docker compose up --build -d

# 3. Verifikasi service aktif dan semua model loaded
curl -s http://localhost:8000/health | python3 -m json.tool
```

**Output yang diharapkan:**
```json
{
  "success": true,
  "data": {
    "status": "ok",
    "service": "ai-service",
    "version": "1.0.0",
    "environment": "production",
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

## ⚙️ Daftar Lengkap Environment Variables

Semua variabel dikonfigurasi melalui file `.env` (diload oleh Pydantic Settings).

| Variabel | Tipe | Default | Wajib | Deskripsi |
|---|---|---|---|---|
| `APP_NAME` | `string` | `LaporKita AI Service` | Tidak | Nama aplikasi service |
| `APP_ENV` | `string` | `development` | Tidak | Environment mode (`development` / `production`) |
| `PORT` | `int` | `8000` | Tidak | Port listen server |
| `HOST` | `string` | `0.0.0.0` | Tidak | Host listen server |
| `LOG_LEVEL` | `string` | `INFO` | Tidak | Tingkat logging (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| **Model Paths** | | | | |
| `CLASSIFICATION_MODEL_PATH` | `string` | `models/yolov11-cls-laporkita.pt` | **Ya** | Path ke file weights YOLOv11 |
| `XGBOOST_MODEL_PATH` | `string` | `models/xgboost-flood-risk.json` | **Ya** | Path ke file model XGBoost |
| **Gemini LLM** | | | | |
| `GEMINI_API_KEY` | `string` | `""` | **Ya** | API Key Google Gemini (dari Google AI Studio) |
| `GEMINI_MODEL_NAME` | `string` | `gemini-2.5-flash` | Tidak | Identifier model Gemini |
| **AI Verification Thresholds** | | | | |
| `AI_CONFIDENCE_THRESHOLD` | `float` | `0.6` | Tidak | Ambang batas minimum confidence untuk auto-approve (`Rules.md §1.2`) |
| **Kota Malang Bounding Box** | | | | |
| `MALANG_BBOX_MIN_LAT` | `float` | `-8.0500` | Tidak | Batas selatan wilayah pilot (Kota Malang) |
| `MALANG_BBOX_MAX_LAT` | `float` | `-7.9000` | Tidak | Batas utara wilayah pilot |
| `MALANG_BBOX_MIN_LON` | `float` | `112.5500` | Tidak | Batas barat wilayah pilot |
| `MALANG_BBOX_MAX_LON` | `float` | `112.7000` | Tidak | Batas timur wilayah pilot |
| **Smart Priority Weights** | | | | |
| `WEIGHT_DAMAGE_SEVERITY` | `float` | `0.35` | Tidak | Bobot keparahan kerusakan (`Rules.md §1.3`) |
| `WEIGHT_SUPPORT_COUNT` | `float` | `0.25` | Tidak | Bobot dukungan/upvote warga |
| `WEIGHT_LOCATION_DENSITY` | `float` | `0.20` | Tidak | Bobot kepadatan laporan di wilayah |
| `WEIGHT_CATEGORY_URGENCY` | `float` | `0.20` | Tidak | Bobot urgensi kategori fasilitas |

---

## 🔀 Routing & URL Mapping (Dual-Prefix)

Service ini mendaftarkan router secara **dual-prefix** untuk mendukung dua klien yang berbeda:

| Klien | URL Prefix | Format Response | Keterangan |
|---|---|---|---|
| **Canonical / Langsung** | `/v1/...` | `{ success, data, error }` envelope standar | Untuk penggunaan langsung / testing |
| **NestJS Backend** | `/api/v1/...` | Sesuai ekspektasi masing-masing service | Terintegrasi dengan `backend-laporkita` |

Pada prefix `/api/v1`, terdapat dua handler untuk `/verify`:
- **`verify_compat_router`** (didaftarkan **pertama**): Mengembalikan response **flat** (tanpa envelope) sesuai ekspektasi `ai-verification.service.js` di NestJS — menang karena prioritas registrasi.
- **`verification_router`**: Fallback dengan format envelope standar.

---

## 📡 Dokumentasi Lengkap Semua Endpoint

### 1. `GET /health`

Mengecek status kesehatan server dan kesiapan operasional semua model ML di memori.

- **URL:** `GET http://localhost:8000/health`
- **Auth:** Tidak diperlukan
- **Response Model:** `APIResponse[HealthStatusData]`

#### Response (HTTP 200 OK — Semua Model Siap):
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

#### Response (HTTP 200 — Status `degraded` jika model gagal load):
```json
{
  "success": true,
  "data": {
    "status": "degraded",
    "models": {
      "yolo_classification_loaded": false,
      "xgboost_risk_loaded": true,
      "gemini_configured": true
    }
  },
  "error": null
}
```

---

### 2. `POST /v1/verify` — Canonical (envelope)

Verifikasi laporan foto kerusakan fasilitas publik warga menggunakan YOLOv11-cls.

- **URL (Canonical):** `POST http://localhost:8000/v1/verify`
- **URL (Via NestJS proxy):** `POST http://localhost:8000/api/v1/verify` *(mengembalikan format berbeda, lihat endpoint #3)*
- **Content-Type:** `application/json`
- **Response Model:** `APIResponse[VerifyReportData]`

#### Pipeline Verifikasi (Rules.md §1.2):
1. Validasi GPS → Apakah koordinat berada di dalam Bounding Box Kota Malang
2. Validasi Timestamp → Apakah timestamp foto tidak anomali (terlalu lampau / masa depan)
3. Inferensi YOLOv11-cls → Klasifikasi gambar ke 5 kelas
4. Decision Rule:
   - `confidence ≥ 0.6` **DAN** GPS valid **DAN** Timestamp valid → `is_valid: true, needs_manual_review: false`
   - Salah satu gagal → `is_valid: false, needs_manual_review: true` (masuk antrean review operator, **bukan ditolak**)
5. Hitung Smart Priority `urgency_score` (Rules.md §1.3)

#### Request Body:
```json
{
  "image_base64": "/9j/4AAQSkZJRgABAQAAAQABAAD...",
  "claimed_category": "Jalan Berlubang",
  "latitude": -7.9826,
  "longitude": 112.6308,
  "timestamp": "2026-08-23T02:00:00Z"
}
```

**Field Aliases (diterima dari NestJS backend-laporkita):**

| Field Standar | Alias NestJS | Keterangan |
|---|---|---|
| `image_url` | `photo_url` | URL publik / pre-signed gambar |
| `claimed_category` | `reported_category` | Kategori dipilih pengguna |
| `timestamp` | `created_at` | Timestamp laporan dibuat |

> **Catatan:** Kirim `image_url` ATAU `image_base64` (minimal salah satu wajib ada).

#### Response (HTTP 200 — Terverifikasi Otomatis):
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

#### Response (HTTP 200 — Perlu Review Manual, GPS di luar Malang):
```json
{
  "success": true,
  "data": {
    "ai_confidence_score": 0.9812,
    "predicted_category": "Trotoar",
    "is_valid": false,
    "needs_manual_review": true,
    "damage_severity": 0.86,
    "urgency_score": 0.451,
    "description_auto": "Terdeteksi kerusakan jalur pejalan kaki/trotoar beton dengan estimasi keparahan 86% (keyakinan AI 98%). Memerlukan perbaikan struktur trotoar.",
    "gps_valid": false,
    "timestamp_valid": true,
    "class_probabilities": { "Trotoar": 0.9812 },
    "_placeholder": false
  },
  "error": null
}
```

#### Response Error (HTTP 422 — Gambar Tidak Dapat Dibaca):
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_IMAGE",
    "message": "Gambar tidak dapat dimuat: format base64 tidak valid atau file corrupt"
  }
}
```

#### Response Error (HTTP 422 — Field Wajib Tidak Ada):
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "latitude: Field required",
    "details": [...]
  }
}
```

#### Keterangan Field `urgency_score`:

```
urgency_score = (0.35 × damage_severity)
              + (0.25 × support_count_normalized)
              + (0.20 × location_density_factor)
              + (0.20 × category_urgency_weight)
```

Nilai `category_urgency_weight` per kategori (default):

| Kategori | Bobot Urgensi |
|---|---|
| Jalan Berlubang | 0.90 |
| Drainase | 0.85 |
| Rambu Lalu Lintas | 0.80 |
| Lampu Jalan | 0.70 |
| Trotoar | 0.65 |

---

### 3. `POST /api/v1/verify` — NestJS Compat (flat)

Endpoint kompatibilitas khusus untuk `backend-laporkita` (NestJS). Menggunakan **pipeline inferensi yang sama** dengan endpoint canonical, namun mengembalikan response **flat** (tanpa wrapper envelope) sesuai kontrak `ai-verification.service.js`.

- **URL:** `POST http://localhost:8000/api/v1/verify`
- **Content-Type:** `application/json`
- **Response Model:** `VerifyReportNestJSData` (flat, tanpa `success`/`error` wrapper)

#### Request Body: (sama dengan endpoint canonical)
```json
{
  "photo_url": "https://storage.laporkita.id/reports/abc123.jpg",
  "reported_category": "Drainase",
  "latitude": -7.9826,
  "longitude": 112.6308,
  "created_at": "2026-08-23T02:00:00Z"
}
```

#### Response (HTTP 200 — Flat):
```json
{
  "confidence": 0.9999,
  "category": "Drainase",
  "is_valid_gps": true,
  "is_valid_timestamp": true,
  "damage_severity": 0.94,
  "reason": "Lolos verifikasi otomatis (AI confidence >= threshold, GPS dan timestamp valid)",
  "is_mock": false
}
```

---

### 4. `POST /v1/predict-risk`

Memprediksi probabilitas risiko genangan air dan tingkat stres wilayah menggunakan model XGBoost baseline.

- **URL (Canonical):** `POST http://localhost:8000/v1/predict-risk`
- **URL (NestJS):** `POST http://localhost:8000/api/v1/predict-risk`
- **Content-Type:** `application/json`
- **Response Model:** `APIResponse[PredictRiskData]`

#### Request Body:
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

| Field | Tipe | Wajib | Rentang | Deskripsi |
|---|---|---|---|---|
| `zone_id` | `string` | Tidak | — | UUID zona urban (ERD.md §2.11) |
| `report_density` | `int` | Tidak (default: 0) | `≥ 0` | Jumlah laporan aktif di zona |
| `weather_context.rainfall_mm` | `float` | Tidak (default: 0.0) | `≥ 0.0` | Curah hujan dalam milimeter |
| `weather_context.temperature_c` | `float` | Tidak (default: 27.0) | — | Suhu ambient dalam Celsius |
| `weather_context.drainage_issue_ratio` | `float` | Tidak (default: 0.2) | `0.0–1.0` | Rasio laporan drainase terhadap total laporan |
| `traffic_density` | `float` | Tidak (default: 0.5) | `0.0–1.0` | Tingkat kemacetan ternormalisasi |

#### Response (HTTP 200 — Risiko Tinggi):
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

#### Response (HTTP 200 — Risiko Rendah):
```json
{
  "success": true,
  "data": {
    "flood_risk_probability": 0.2134,
    "risk_level": "low",
    "predicted_stress_level": "low",
    "factors": {
      "rainfall_impact": 0.05,
      "report_density_impact": 0.025,
      "traffic_congestion_impact": 0.2,
      "drainage_vulnerability_impact": 0.1
    },
    "recommendation": "Kondisi wilayah normal. Pemantauan rutin DPUPR cukup memadai.",
    "_placeholder": false
  },
  "error": null
}
```

**Level Risiko:**

| `flood_risk_probability` | `risk_level` / `predicted_stress_level` |
|---|---|
| `< 0.4` | `low` |
| `0.4 – 0.7` | `medium` |
| `> 0.7` | `high` |

---

### 5. `POST /v1/predict/zone-metrics` — NestJS Compat

Endpoint kompatibilitas khusus untuk NestJS `prediction.service.js`. Menerima input sederhana (`zone_id`, `active_reports`) dan secara internal mengestimasikan parameter cuaca dari jumlah laporan aktif, lalu menjalankan XGBoost inference yang sama.

- **URL (Canonical):** `POST http://localhost:8000/v1/predict/zone-metrics`
- **URL (NestJS):** `POST http://localhost:8000/api/v1/predict/zone-metrics`
- **Content-Type:** `application/json`
- **Response Model:** `PredictZoneMetricsData` (flat, tanpa envelope)

#### Request Body:
```json
{
  "zone_id": "b2c3d4e5-f6a7-8901-bcde-f01234567890",
  "zone_name": "Klojen Pusat",
  "active_reports": 18
}
```

#### Response (HTTP 200):
```json
{
  "report_density": 18,
  "traffic_density": 0.72,
  "flood_risk_probability": 0.7123,
  "weather_context": {
    "source": "BMKG Kota Malang (Simulasi)",
    "temperature_celsius": 24.5,
    "humidity_percentage": 82.0,
    "rainfall_mm": 91.0,
    "condition": "Hujan Deras"
  },
  "stress_level": "high"
}
```

> **Catatan Internal:** `rainfall_mm` diestimasi dengan rumus `min(100, active_reports × 4.5 + 10)` dan `traffic_density` dengan `min(0.95, 0.3 + active_reports × 0.05)`.

---

### 6. `POST /v1/policy-simulate`

Mensimulasikan skenario intervensi kebijakan pemerintah kota menggunakan Google Gemini 2.5 Flash dengan output JSON terstruktur yang divalidasi oleh Pydantic.

- **URL (Canonical):** `POST http://localhost:8000/v1/policy-simulate`
- **URL (NestJS):** `POST http://localhost:8000/api/v1/policy-simulate`
- **Content-Type:** `application/json`
- **Response Model:** `APIResponse[PolicySimulateData]`
- **Timeout:** 20 detik (Gemini API)

#### Request Body:
```json
{
  "prompt_text": "Bagaimana proyeksi dampak jika Pemkot Malang mengalokasikan anggaran Rp 1.5 Miliar untuk normalisasi gorong-gorong di sepanjang koridor Jalan Soekarno-Hatta menjelang musim hujan?",
  "zone_id": "zone-lowokwaru-suhat",
  "time_horizon_months": 6,
  "parameters": {
    "allocated_budget_idr": 1500000000,
    "target_district": "Lowokwaru",
    "priority_facility": "Drainase"
  }
}
```

| Field | Tipe | Wajib | Batasan | Deskripsi |
|---|---|---|---|---|
| `prompt_text` | `string` | **Ya** | `5–2000 karakter` | Skenario kebijakan yang diajukan |
| `zone_id` | `string` | Tidak | — | UUID zona target jika simulasi terlokalisir |
| `time_horizon_months` | `int` | Tidak (default: 6) | `1–60` | Durasi simulasi dalam bulan |
| `parameters` | `object` | Tidak | — | Parameter tambahan (anggaran, tipe intervensi, dll.) |

#### Response (HTTP 200 — Berhasil):
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

#### Response Error (HTTP 504 — Gemini Timeout):
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "GEMINI_TIMEOUT",
    "message": "Gemini API request melebihi batas waktu (20 detik)."
  }
}
```

#### Response Error (HTTP 502 — Format Tidak Valid dari Gemini):
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "GEMINI_INVALID_RESPONSE",
    "message": "Gemini mengembalikan format respons yang tidak dapat divalidasi."
  }
}
```

---

## 📐 Format Response Envelope Standar

Semua endpoint canonical (`/v1/...`) menggunakan format response envelope standar (`Rules.md §3`):

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Deskripsi error yang jelas",
    "details": [ ... ]
  }
}
```

> **Catatan:** Endpoint NestJS Compat (`/api/v1/verify`, `/v1/predict/zone-metrics`) mengembalikan format **flat** tanpa envelope sesuai kontrak NestJS.

---

## 🚨 Error Codes & HTTP Status Reference

| HTTP Status | Error Code | Trigger |
|---|---|---|
| `422` | `VALIDATION_ERROR` | Field wajib tidak ada atau tipe data salah |
| `422` | `INVALID_IMAGE` | Gambar tidak dapat dibaca (corrupt / base64 invalid) |
| `502` | `GEMINI_INVALID_RESPONSE` | Gemini mengembalikan JSON tidak valid / gagal parse |
| `504` | `GEMINI_TIMEOUT` | Gemini API tidak merespons dalam 20 detik |
| `500` | `INTERNAL_SERVER_ERROR` | Error tidak terduga di sisi server |
| `404` | `HTTP_404` | Endpoint tidak ditemukan |

---

## 📊 Ringkasan Dataset Publik (5 Kategori)

Rincian lengkap, URL verifikasi, dan analisis domain gap didokumentasikan di [`dataset_report.md`](dataset_report.md).

| Kategori LaporKita | Nama Dataset Publik | URL Sumber | Lisensi | Total Clean | Train (70%) | Val (15%) | Test (15%) |
|---|---|---|---|---|---|---|---|
| **Jalan Berlubang** | Roboflow Pothole / RDD2022 subset | [HuggingFace: keremberke/pothole-segmentation](https://huggingface.co/datasets/keremberke/pothole-segmentation) | CC BY 4.0 | **486** | 340 | 72 | 74 |
| **Trotoar** | METU Concrete Crack Images (CCIC) | [Mendeley Data: 5y9wdsg2zt.2](https://data.mendeley.com/datasets/5y9wdsg2zt/2) | CC BY 4.0 | **600** | 420 | 90 | 90 |
| **Rambu Lalu Lintas** | German Traffic Sign Detection (GTSDB) | [HuggingFace: keremberke/german-traffic-sign-detection](https://huggingface.co/datasets/keremberke/german-traffic-sign-detection) | CC BY 4.0 | **491** | 343 | 73 | 75 |
| **Lampu Jalan** | Team16 Street Light Dataset | [GitHub: Team16Project/Street-Light-Dataset](https://github.com/Team16Project/Street-Light-Dataset) | MIT | **447** | 312 | 67 | 68 |
| **Drainase** | Manhole Covers & Storm Drains | [HuggingFace: delima87/manhole_covers_dataset](https://huggingface.co/datasets/delima87/manhole_covers_dataset) | CC BY 4.0 | **545** | 381 | 81 | 83 |
| **TOTAL** | | | | **2.569** | **1.796** | **383** | **390** |

---

## 📈 Metrik Evaluasi Model Riil

### A. YOLOv11-cls Computer Vision (Test Set: 390 Citra, Independen)

*Evaluasi dijalankan pada held-out test set independen (`dataset/test/`) — bukan training set.*

| Metrik | Nilai |
|---|---|
| **Top-1 Accuracy** | **99.49%** (388/390 benar) |
| **Macro Average F1-Score** | **99.48%** |
| **Kecepatan Inferensi (MPS GPU)** | **~2.1 ms / citra** |
| **Model Architecture** | `yolo11n-cls` (Nano Classifier) |
| **Training Data** | 1.796 citra (70% stratified split) |
| **Pretrained From** | ImageNet (Transfer Learning) |

**Per-Class Precision / Recall / F1:**

| Kategori Fasilitas | Precision | Recall | F1-Score | Support (Test Samples) |
|---|---|---|---|---|
| **Drainase** | 0.9880 | 0.9880 | **0.9880** | 83 |
| **Jalan Berlubang** | 1.0000 | 0.9865 | **0.9932** | 74 |
| **Lampu Jalan** | 0.9855 | 1.0000 | **0.9927** | 68 |
| **Rambu Lalu Lintas** | 1.0000 | 1.0000 | **1.0000** | 75 |
| **Trotoar** | 1.0000 | 1.0000 | **1.0000** | 90 |

*Laporan evaluasi mendalam (confusion matrix, per-class error analysis, training curves) tersedia di [`training_report.md`](training_report.md).*

---

### B. XGBoost Risk Prediction (Test Set: 1.200 Sampel Sintetis)

*Evaluasi pada 20% held-out dari total 6.000 sampel dataset sintetis hidrologi perkotaan.*

| Metrik | Nilai |
|---|---|
| **R² Score** | **0.9635** |
| **RMSE** | **0.0490** |
| **MAE** | **0.0369** (rata-rata deviasi probabilitas ±3.69%) |
| **Model Architecture** | `XGBRegressor` (`n_estimators=300, max_depth=6, learning_rate=0.05`) |
| **Training Data** | 4.800 sampel sintetis (80% dari 6.000) |

---

## 🏗️ Arsitektur Decision Log

Berikut adalah keputusan teknis utama yang dibuat selama pengembangan:

| Keputusan | Pilihan | Alternatif Dipertimbangkan | Alasan |
|---|---|---|---|
| **Model klasifikasi** | `yolo11n-cls` (Nano) | CLIP, MobileNet, ResNet50 | Ekosistem Ultralytics mature, inference sangat cepat (~2ms), mudah di-retrain dengan foto lokal |
| **Deployment model** | Model weights di-copy ke Docker image | Volume mount dari host | Container benar-benar mandiri (*self-contained*), tidak ada external dependency saat runtime |
| **Dockerfile** | Single-stage dengan CPU PyTorch | Multi-stage build | Multi-stage gagal karena Docker Desktop memory limit saat download CUDA packages (>1GB); CPU PyTorch cukup untuk inference |
| **Dataset strategi** | Public datasets + proxy visual | Scraping foto laporan lokal | Zero foto lapangan Kota Malang tersedia; proxy public datasets memungkinkan training dapat langsung dijalankan |
| **Data historis XGBoost** | Sintetis (aturan hidrologi) | BMKG API + laporan DPUPR | Data historis riil belum tersedia; synthetic data cukup untuk demo dan memperlihatkan pola prediksi yang masuk akal |
| **Dual-prefix routing** | `/v1/...` + `/api/v1/...` | Satu prefix saja | NestJS backend-laporkita memanggil `/api/v1/...`; prefix canonical `/v1/...` dipertahankan untuk backward compatibility dan testing |
| **NestJS compat response** | Flat response schema terpisah (`VerifyReportNestJSData`) | Transform di NestJS | Menghindari parsing ganda di NestJS layer; AI Service bertanggung jawab penuh atas format yang dikonsumsinya |

---

## ⚠️ Disclaimer & Known Limitations (Produksi)

Untuk keterbukaan teknis (*technical honesty*) sebelum deployment ke production sesungguhnya:

### 1. Domain Shift — Zero Field Validation Kota Malang

Model YOLOv11 dievaluasi pada held-out test set dari dataset publik (akurasi 99.49%). **Belum ada validasi dengan foto lapangan warga asli Kota Malang.** Performa aktual di lapangan dapat terpengaruh oleh:
- Sudut pengambilan foto yang tidak ideal (foto dari jarak jauh, sudut miring)
- Kamera ponsel resolusi rendah atau kondisi pencahayaan ekstrem (malam hari, backlight)
- Tampilan fisik kerusakan infrastruktur lokal yang berbeda dari dataset publik internasional

**Rekomendasi:** Lakukan labeling 200–500 foto lapangan warga Malang per kategori dan fine-tune model sebelum production launch.

### 2. Kategori Proxy Visual

| Kategori | Dataset yang Digunakan | Gap Representasi |
|---|---|---|
| **Trotoar** | Concrete Crack Images (pelat beton) | Belum mencakup paving block warna, trotoar tanah, kanstin rusak |
| **Drainase** | Manhole covers & grill saluran air | Belum mencakup parit terbuka, selokan batu bata, saluran lahan sawah |
| **Rambu Lalu Lintas** | GTSDB (standar Eropa) | Piktogram minor berbeda dari rambu Dishub/Kemenhub RI |

### 3. Data Historis XGBoost Sintetis

Model XGBoost dilatih pada **6.000 sampel sintetis** yang dihasilkan berdasarkan aturan hidrologi perkotaan logistik (`scripts/generate_synthetic_zone_data.py`). Dataset ini **BUKAN data observasi riil**.

> **WAJIB di-retrain** dengan data historis riil (deret waktu curah hujan stasiun BMKG Karangploso + log penanganan fisik DPUPR Kota Malang) sebelum digunakan untuk pengambilan keputusan anggaran atau kebijakan publik yang sesungguhnya.

### 4. Metrik `damage_severity` sebagai Proxy

Nilai `damage_severity` (0.0–1.0) adalah **estimasi terkalibrasi** dari confidence model klasifikasi dan bobot urgensi kelas per kategori. Ini **bukan pengukuran langsung** luas fisik kerusakan per meter persegi. Untuk kuantifikasi kerusakan yang akurat, diperlukan model segmentasi (SAM/Mask R-CNN) atau survei fisik lapangan.
