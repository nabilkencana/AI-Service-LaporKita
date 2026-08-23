<div align="center">

# 🧠 LaporKita AI Service

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0.110%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/YOLOv11--cls-99.56%25%20Acc%20(6%20Classes)-FF6B35?style=for-the-badge&logo=pytorch&logoColor=white" />
  <img src="https://img.shields.io/badge/XGBoost-R²%3D0.9635%20(sintetis)-F7931E?style=for-the-badge" />
  <img src="https://img.shields.io/badge/DeepSeek%20API-LLM-0066FF?style=for-the-badge&logo=deepseek&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-Containerized-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/Tests-35%20Passing-brightgreen?style=for-the-badge&logo=pytest&logoColor=white" />
</p>

> **Microservice Python FastAPI** mandiri untuk platform **LaporKita** — platform pelaporan kerusakan infrastruktur publik **Kota Malang** berbasis AI.
>
> Menyediakan tiga kapabilitas AI/ML end-to-end: **Computer Vision verifikasi laporan**, **Urban Risk Prediction**, dan **Policy Impact Simulation** berbasis LLM.

</div>

---

## 📑 Daftar Isi

- [🌐 Gambaran Umum Platform](#-gambaran-umum-platform)
- [🏛️ Arsitektur Sistem](#️-arsitektur-sistem)
  - [Topologi Microservice](#topologi-microservice)
  - [Alur Data End-to-End](#alur-data-end-to-end)
  - [Alur Verifikasi AI](#alur-verifikasi-ai)
  - [Alur Prediksi Risiko](#alur-prediksi-risiko)
  - [Alur Policy Simulator](#alur-policy-simulator)
- [🧩 Teknologi Stack](#-teknologi-stack)
- [📁 Struktur Direktori Proyek](#-struktur-direktori-proyek)
- [🚀 Cara Menjalankan Lokal](#-cara-menjalankan-lokal-venv)
- [🐳 Cara Menjalankan dengan Docker](#-cara-menjalankan-dengan-docker)
- [⚙️ Environment Variables](#️-daftar-lengkap-environment-variables)
- [🔀 Routing & URL Mapping](#-routing--url-mapping-dual-prefix)
- [📡 Dokumentasi Lengkap Semua Endpoint](#-dokumentasi-lengkap-semua-endpoint)
  - [GET /health](#1-get-health)
  - [GET /demo & GET / — Interactive Web Console](#2-get-demo--get----interactive-web-console)
  - [POST /v1/verify — Canonical](#3-post-v1verify--canonical-envelope)
  - [POST /api/v1/verify — NestJS Compat](#4-post-apiv1verify--nestjs-compat-flat)
  - [POST /v1/predict-risk](#5-post-v1predict-risk)
  - [POST /v1/predict/zone-metrics](#6-post-v1predictzone-metrics--nestjs-compat)
  - [POST /v1/policy-simulate](#7-post-v1policy-simulate)
- [📐 Format Response Envelope](#-format-response-envelope-standar)
- [🚨 Error Codes & HTTP Status Reference](#-error-codes--http-status-reference)
- [📊 Dataset & Training](#-ringkasan-dataset-publik-5-kategori)
- [📈 Metrik Evaluasi Model](#-metrik-evaluasi-model-riil)
- [🏗️ Arsitektur Decision Log](#️-arsitektur-decision-log)
- [⚠️ Disclaimer & Known Limitations](#️-disclaimer--known-limitations-produksi)

---

## 🌐 Gambaran Umum Platform

LaporKita adalah platform **pelaporan kerusakan infrastruktur publik** berbasis AI untuk Kota Malang. Warga dapat melaporkan kerusakan jalan, drainase, lampu jalan, rambu lalu lintas, dan trotoar melalui aplikasi mobile. AI Service berperan sebagai **otak analitik** platform ini.

```mermaid
graph LR
    Citizen["👤 Warga Kota Malang"]
    Mobile["📱 Mobile App\n(Flutter)"]
    Backend["🖥️ Backend Gateway\n(NestJS :3000)"]
    AI["🤖 AI Microservice\n(FastAPI :8000)"]
    DB[("🗄️ PostgreSQL\n+ PostGIS")]
    Gov["🏛️ Dashboard\nPemerintah Kota"]

    Citizen -->|"Foto + GPS + Kategori"| Mobile
    Mobile -->|"REST API"| Backend
    Backend -->|"Internal HTTP"| AI
    AI -->|"Verifikasi + Skor"| Backend
    Backend --> DB
    DB --> Gov
    Gov -->|"Tindak lanjut"| Citizen

    style AI fill:#FF6B35,color:#fff,stroke:#FF6B35
    style Mobile fill:#4285F4,color:#fff
    style Backend fill:#34A853,color:#fff
    style Gov fill:#9B59B6,color:#fff
```

**Tiga Kapabilitas AI Utama:**

| # | Fitur | Model | Performa |
|---|---|---|---|
| 1 | 🔍 **AI Verification** | YOLOv11-cls (Computer Vision) | 99.23% Test Accuracy (Leak-Free Split) |
| 2 | 📊 **Urban Risk Prediction** | XGBoost Regressor | R² = 0.9635, RMSE = 0.0490 (Baseline Sintetis) |
| 3 | 🧬 **Policy Simulator** | DeepSeek API (LLM) | Structured JSON output, 20s timeout |

---

## 🏛️ Arsitektur Sistem

### Topologi Microservice

```mermaid
graph TB
    subgraph Client["📱 Client Layer"]
        Flutter["Flutter Mobile App"]
    end

    subgraph Gateway["🖥️ Backend Gateway (NestJS :3000)"]
        NestAuth["Auth Service"]
        NestAI["AI Verification Service\n(ai-verification.service.js)"]
        NestPred["Prediction Service\n(prediction.service.js)"]
        NestPolicy["Policy Service\n(policy.service.js)"]
    end

    subgraph AIService["🤖 AI Microservice (FastAPI :8000)"]
        direction TB
        Router["FastAPI Router\n(Dual-Prefix)"]

        subgraph Endpoints["Endpoints"]
            Verify["/v1/verify\n/api/v1/verify"]
            Risk["/v1/predict-risk\n/v1/predict/zone-metrics"]
            Policy["/v1/policy-simulate"]
            Health["/health"]
        end

        subgraph Services["Services Layer"]
            YOLOSvc["YOLOService\n(Singleton, Thread-Safe)"]
            XGBSvc["XGBoostService\n(Singleton, Lazy-Loaded)"]
            LLMSvc["DeepSeekService\n(20s Timeout, Injection Guard)"]
        end

        subgraph Utils["Utils Layer"]
            GPS["GPS Validator\n(Malang BBox)"]
            Scoring["Smart Priority\nScoring"]
        end

        subgraph Models["🧠 Model Weights"]
            YOLO["yolov11-cls-laporkita.pt\n(5-class, ~5.5MB)"]
            XGB["xgboost-flood-risk.json\nR2=0.9635"]
        end
    end

    subgraph Infra["☁️ Infrastructure"]
        PG[("PostgreSQL\n+ PostGIS")]
        Redis[("Redis Cache")]
        Minio["Minio\nObject Storage"]
    end

    Flutter --> NestAuth
    Flutter --> Gateway
    NestAI -->|"POST /api/v1/verify"| Verify
    NestPred -->|"POST /api/v1/predict-risk\nPOST /api/v1/predict/zone-metrics"| Risk
    NestPolicy -->|"POST /api/v1/policy-simulate"| Policy

    Router --> Endpoints
    Verify --> YOLOSvc
    Verify --> GPS
    Verify --> Scoring
    Risk --> XGBSvc
    Policy --> LLMSvc

    YOLOSvc --> YOLO
    XGBSvc --> XGB
    LLMSvc --> DeepSeek

    Gateway --> PG
    Gateway --> Redis
    Gateway --> Minio

    style AIService fill:#FFF3E0,stroke:#FF6B35,stroke-width:2px
    style Models fill:#E8F5E9,stroke:#34A853
    style Infra fill:#E3F2FD,stroke:#1976D2
```

---

### Alur Data End-to-End

```mermaid
sequenceDiagram
    actor Warga
    participant Flutter as 📱 Flutter App
    participant NestJS as 🖥️ NestJS Backend
    participant FastAPI as 🤖 FastAPI AI Service
    participant YOLO as 🧠 YOLOv11-cls
    participant XGB as 📊 XGBoost
    participant DeepSeek as 🤖 DeepSeek API
    participant DB as 🗄️ PostgreSQL

    Warga->>Flutter: Foto + GPS + Kategori
    Flutter->>NestJS: POST /reports (multipart)
    NestJS->>FastAPI: POST /api/v1/verify (image_base64 / photo_url)

    FastAPI->>FastAPI: Validasi GPS (Malang BBox)
    FastAPI->>FastAPI: Validasi Timestamp
    FastAPI->>YOLO: Inferensi klasifikasi 5 kelas (Non-blocking thread)
    YOLO-->>FastAPI: class_probabilities + confidence + severity
    FastAPI->>FastAPI: Hitung smart_priority_score
    FastAPI-->>NestJS: confidence, category, is_valid, smart_priority_score

    NestJS->>DB: Simpan laporan + skor
    NestJS-->>Flutter: Report ID + status

    Note over NestJS, FastAPI: Paralel — Urban Risk Assessment
    NestJS->>FastAPI: POST /api/v1/predict/zone-metrics
    FastAPI->>XGB: Inferensi flood risk
    XGB-->>FastAPI: flood_risk_probability
    FastAPI-->>NestJS: risk_level + recommendation

    Note over NestJS, FastAPI: Opsional — Policy Simulation
    NestJS->>FastAPI: POST /api/v1/policy-simulate
    FastAPI->>DeepSeek: Structured JSON prompt (Strict Injection Guard)
    DeepSeek-->>FastAPI: Narasi + projected_data (Redacted & Schema Enforced)
    FastAPI-->>NestJS: result_narrative + key_recommendations

    NestJS->>DB: Update zone risk metrics
    Warga->>Flutter: Terima notifikasi tindak lanjut
```

---

### Alur Verifikasi AI

```mermaid
flowchart TD
    Input(["📥 Input Request\nimage_base64 / photo_url\n+ GPS + timestamp + category"])

    GPS{"🗺️ GPS dalam\nBounding Box\nKota Malang?"}
    TS{"🕐 Timestamp\nValid?\ntidak anomali"}
    YOLO["🧠 YOLOv11-cls Inference\n~2.1ms per image\n5 kelas output"]
    CONF{"🎯 Confidence\nbig-or-equal threshold\ndefault: 0.60?"}

    AutoApprove(["✅ is_valid: true\nneeds_manual_review: false\nAUTO-APPROVED"])
    ManualReview(["⚠️ is_valid: false\nneeds_manual_review: true\nQUEUED FOR REVIEW"])

    Score["📊 Hitung urgency_score\n= 0.35 x severity\n+ 0.25 x support\n+ 0.20 x density\n+ 0.20 x category_weight"]

    Response(["📤 Response JSON\nai_confidence_score\npredicted_category\nurgency_score\nclass_probabilities"])

    Error422(["❌ HTTP 422\nINVALID_IMAGE\nor VALIDATION_ERROR"])

    Input --> GPS
    GPS -->|"❌ Di luar Malang"| ManualReview
    GPS -->|"✅ Dalam Malang"| TS
    TS -->|"❌ Anomali"| ManualReview
    TS -->|"✅ Valid"| YOLO
    YOLO -->|"Gagal decode gambar"| Error422
    YOLO --> CONF
    CONF -->|"✅ Ya"| AutoApprove
    CONF -->|"❌ Tidak"| ManualReview

    AutoApprove --> Score
    ManualReview --> Score
    Score --> Response

    style AutoApprove fill:#E8F5E9,stroke:#34A853,color:#1B5E20
    style ManualReview fill:#FFF8E1,stroke:#F9A825,color:#F57F17
    style Error422 fill:#FFEBEE,stroke:#C62828,color:#B71C1C
    style YOLO fill:#E3F2FD,stroke:#1976D2,color:#0D47A1
```

---

### Alur Prediksi Risiko

```mermaid
flowchart LR
    subgraph Input["📥 Input"]
        ZoneID["zone_id"]
        ReportDens["report_density"]
        Weather["weather_context\nrainfall_mm, temp_c\ndrainage_issue_ratio"]
        Traffic["traffic_density"]
    end

    subgraph ZoneMetrics["🔄 /zone-metrics\nNestJS Compat"]
        Estimate["Estimasi parameter\ndari active_reports\nrainfall = min(100, Nx4.5+10)\ntraffic = min(0.95, 0.3+Nx0.05)"]
    end

    subgraph XGB["🧠 XGBoost Inference"]
        Feature["Feature Matrix\n5 fitur\nPandas DataFrame"]
        Model["XGBRegressor\nn_estimators=300\nmax_depth=6, lr=0.05"]
        Prob["flood_risk_probability\n0.0 to 1.0"]
    end

    subgraph RiskLevel["📊 Risk Classification"]
        Low["🟢 LOW\n< 0.40"]
        Medium["🟡 MEDIUM\n0.40 to 0.70"]
        High["🔴 HIGH\n> 0.70"]
    end

    subgraph Output["📤 Output"]
        Resp["risk_level\npredicted_stress_level\nfactors breakdown\nrecommendation text"]
    end

    Input --> Feature
    ZoneMetrics --> Feature
    Feature --> Model
    Model --> Prob
    Prob --> Low
    Prob --> Medium
    Prob --> High
    Low & Medium & High --> Resp

    style High fill:#FFEBEE,stroke:#C62828
    style Medium fill:#FFF8E1,stroke:#F9A825
    style Low fill:#E8F5E9,stroke:#34A853
```

---

### Alur Policy Simulator

```mermaid
sequenceDiagram
    participant Client as 🖥️ NestJS / Client
    participant Router as 🔀 FastAPI Router
    participant DeepSeek as 🤖 DeepSeek API
    participant Guard as 🛡️ Prompt Guard & Pydantic

    Client->>Router: POST /v1/policy-simulate (prompt_text, zone_id, time_horizon)
    Router->>Router: Validasi panjang input (5 s.d. 2000 karakter)

    alt API Key Tidak Dikonfigurasi
        Router-->>Client: 503 LLM_KEY_NOT_CONFIGURED
    else API Key Valid
        Router->>DeepSeek: Structured JSON request (deepseek-chat, max 20s timeout)
        alt Berhasil kurang dari 20 detik
            DeepSeek-->>Router: Raw JSON response
            Router->>Guard: Sanitasi Keyword Injeksi & Validasi Pydantic
            alt Format & Skema Valid
                Guard-->>Router: Parsed PolicySimulateData
                Router-->>Client: 200 OK (narrative, result_data, recommendations)
            else Format Tidak Valid
                Guard-->>Router: ValidationError / JSONDecodeError
                Router-->>Client: 502 LLM_INVALID_RESPONSE
            end
        else Timeout lebih dari 20 detik
            DeepSeek-->>Router: TimeoutException
            Router-->>Client: 504 LLM_TIMEOUT
        end
    end
```

---

## 🧩 Teknologi Stack

```mermaid
graph LR
    subgraph API["🌐 API Layer"]
        FastAPI["FastAPI >= 0.110\nASGI + OpenAPI"]
        Uvicorn["Uvicorn >= 0.28\nuvloop ASGI"]
        Pydantic["Pydantic v2 >= 2.6\nValidation + Settings"]
        Console["Web Console (HTML5/JS)\nindex.html at /demo"]
    end

    subgraph AI["🧠 AI/ML Layer"]
        YOLO["Ultralytics >= 8.3\nYOLOv11-cls (3.0 MB)"]
        XGB["XGBoost >= 2.0\nXGBRegressor (497 KB)"]
        DeepSeek["DeepSeek API\ndeepseek-chat via httpx"]
        PIL["Pillow >= 10.0\nImage Processing"]
        Pandas["Pandas >= 2.0\n+ NumPy >= 1.24\nFeature Matrix"]
    end

    subgraph Infra["☁️ Infrastructure"]
        Docker["Docker + Compose\nSelf-Contained (3.5 MB weights)"]
        Sec["Security Layer\nSSRF & 8MB Guard"]
    end

    FastAPI --> YOLO
    FastAPI --> XGB
    FastAPI --> DeepSeek
    FastAPI --> Console
    Uvicorn --> FastAPI
    Pydantic --> FastAPI
    YOLO --> PIL
    XGB --> Pandas
    Docker --> FastAPI
    Sec --> FastAPI
```

| Layer | Teknologi | Versi | Peran |
|---|---|---|---|
| Web Framework | **FastAPI** | `>=0.110.0` | ASGI routing, Pydantic validation, OpenAPI docs |
| ASGI Server | **Uvicorn** | `>=0.28.0` | Production ASGI server with uvloop |
| Interactive Console | **Vanilla JS + HTML5** | Modern Web | Interactive Console di `GET /` & `GET /demo` |
| Computer Vision | **Ultralytics YOLOv11** | `>=8.3.0` | Image classification (5-class, `-cls` mode) |
| ML Baseline | **XGBoost** | `>=2.0.0` | Risk regression (`XGBRegressor`) |
| LLM | **DeepSeek API** | `deepseek-chat` via `httpx` | Structured JSON policy simulation with injection guard |
| Async HTTP Client | **HTTPX** | `>=0.27.0` | Non-blocking async client for DeepSeek API |
| Image Processing | **Pillow** | `>=10.0.0` | Base64 decode, URL fetch, YOLO pre-processing |
| Data Processing | **Pandas + NumPy** | `>=2.0.0 / >=1.24.0` | XGBoost feature matrix |
| Validation | **Pydantic v2** | `>=2.6.0` | Schema + settings validation |
| Config | **Pydantic Settings** | `>=2.2.0` | Environment variables dari `.env` |
| Containerization | **Docker + Compose** | — | Self-contained deployment |

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
│   │   ├── yolo_service.py         # Singleton YOLOv11 classifier (thread-safe, pre-warmed)
│   │   ├── xgboost_service.py      # Singleton XGBoost risk predictor
│   │   ├── deepseek_service.py     # DeepSeek LLM service with prompt injection guard
│   │   └── gemini_service.py       # Fallback LLM interface
│   ├── utils/
│   │   ├── security.py             # SSRF protection, IP resolver blocker, image validator
│   │   ├── gps_validator.py        # Malang bbox check + timestamp validation
│   │   └── scoring.py              # Smart Priority score calculation (Rules.md §1.3)
│   └── main.py                     # FastAPI app, lifespan, global error handlers, demo router
│
├── index.html                      # Interactive Web Console (Live Testing UI)
├── LIMITATIONS.md                  # Laporan batasan teknis ilmiah & kejujuran domain
├── training_report.md              # Metrik evaluasi riil YOLOv11 (99.23% leak-free test accuracy)
├── models/
│   ├── yolov11-cls-laporkita.pt    # Trained YOLOv11-cls model weights (5 classes, 3.0 MB)
│   └── xgboost-flood-risk.json     # Trained XGBoost regressor weights (497 KB)
│
├── scripts/
│   ├── rebuild_clean_dataset.py    # dHash <=8 clustering & video-grouping (LEAK-1 fix)
│   ├── train_yolo_classifier.py    # Training YOLOv11-cls + 180° rotation augmentation
│   ├── generate_synthetic_zone_data.py  # Synthetic dataset 6.000 sampel hidrologi
│   └── train_xgboost_model.py      # Training XGBoost + evaluasi
│
├── tests/
│   ├── test_health.py              # Health check + model readiness verification
│   ├── test_verification.py        # 9 test cases: 5 kelas, GPS, timestamp, category validation, fail-closed
│   ├── test_prediction.py          # 4 test cases: stress rendah/tinggi, boundary, fail-closed
│   ├── test_security.py            # 5 test cases: SSRF loopback/metadata, path traversal, >8MB size, concurrency
│   ├── test_policy_simulator.py    # 6 test cases: DeepSeek mock, 502 parse, 504 timeout, 503 key, injection guard
│   └── test_utils.py               # 7 test cases: GPS bbox, timestamp edge cases, scoring formula
│
├── dataset/
│   ├── train/                      # 1.796 gambar (70%), leak-free split
│   ├── val/                        # 383 gambar (15%), early stopping
│   └── test/                       # 390 gambar (15%), held-out final evaluation
│
├── dataset_report.md               # Dokumentasi lengkap sumber dataset, lisensi, distribusi
├── Architecture.md                 # Arsitektur teknis detail
├── Design.md                       # Design decisions & patterns
├── ERD.md                          # Entity Relationship Diagram
├── PRD.md                          # Product Requirements Document
├── Rules.md                        # Business rules & thresholds
│
├── Dockerfile                      # Single-stage, CPU PyTorch, model weights di-copy ke image
├── docker-compose.yml              # Stack orchestration + env injection
├── requirements.txt                # Pinned dependencies
├── pytest.ini                      # pytest asyncio configuration
├── .env.example                    # Template environment variables
└── README.md
```

**Dependensi antar modul:**

```mermaid
graph TD
    Main["main.py\nFastAPI App + Lifespan"] --> VR["routers/verification.py"]
    Main --> PR["routers/prediction.py"]
    Main --> PSR["routers/policy_simulator.py"]

    VR --> YS["services/yolo_service.py"]
    VR --> GPS["utils/gps_validator.py"]
    VR --> SC["utils/scoring.py"]
    VR --> VS["schemas/verification.py"]

    PR --> XS["services/xgboost_service.py"]
    PR --> PDS["schemas/prediction.py"]

    PSR --> GS["services/gemini_service.py"]
    PSR --> PS["schemas/policy_simulator.py"]

    YS --> YOLO["models/yolov11-cls-laporkita.pt"]
    XS --> XGB["models/xgboost-flood-risk.json"]

    Main --> CFG["core/config.py\nPydantic Settings"]
    Main --> LOG["core/logging.py"]
    VR & PR & PSR --> BASE["schemas/base.py\nAPIResponse[T]"]

    style Main fill:#FF6B35,color:#fff
    style YOLO fill:#E8F5E9,stroke:#34A853
    style XGB fill:#E8F5E9,stroke:#34A853
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
# Edit .env dan isi DEEPSEEK_API_KEY dengan API key dari https://platform.deepseek.com

# 5. Jalankan unit test (32 tests, 100% passing)
pytest -v

# 6. Jalankan server FastAPI
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

> **⚠️ Perhatian:** Gunakan `app.main:app` (bukan `main:app`). Service memerlukan model weights di `models/yolov11-cls-laporkita.pt` (3.0 MB) dan `models/xgboost-flood-risk.json` (497 KB).

Setelah server aktif, buka:
- **Interactive Web Console (Demo UI):** `http://localhost:8000/demo` atau `http://localhost:8000/`
- **Swagger UI (Interaktif):** `http://localhost:8000/docs`
- **ReDoc (Dokumentasi):** `http://localhost:8000/redoc`
- **OpenAPI JSON Schema:** `http://localhost:8000/openapi.json`

---

## 🐳 Cara Menjalankan dengan Docker

Service dikemas sebagai container **mandiri** (*self-contained*) — model weights sudah ter-copy ke dalam image saat `docker build`.

### Lifecycle Container

```mermaid
stateDiagram-v2
    [*] --> Building : docker compose up --build
    Building --> Starting : Image built, model weights embedded
    Starting --> HealthCheck : Uvicorn listening port 8000

    state HealthCheck {
        [*] --> LoadYOLO : Lifespan startup
        LoadYOLO --> LoadXGB
        LoadXGB --> Ready
        Ready --> [*]
    }

    HealthCheck --> Running : /health status ok
    Running --> Degraded : Model load failure
    Running --> Stopped : docker compose down
    Degraded --> [*]
    Stopped --> [*]
```

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
  -e DEEPSEEK_API_KEY=your_api_key_here \
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

Semua variabel dikonfigurasi melalui file `.env` (diload oleh Pydantic Settings dari `app/core/config.py`).

```mermaid
graph LR
    ENV[".env file"] --> PS["Pydantic Settings\ncore/config.py"]
    PS --> App["APP_NAME\nAPP_ENV\nPORT\nHOST\nLOG_LEVEL"]
    PS --> LLMConf["DeepSeek Config\nDEEPSEEK_API_KEY\nDEEPSEEK_MODEL_NAME"]
    PS --> Thresh["AI Thresholds\nAI_CONFIDENCE_THRESHOLD"]
    PS --> BBox["Malang BBox\nMALANG_BBOX_MIN_LAT\nMALANG_BBOX_MAX_LAT\nMALANG_BBOX_MIN_LON\nMALANG_BBOX_MAX_LON"]
    PS --> Weights["Priority Weights\nWEIGHT_DAMAGE_SEVERITY\nWEIGHT_SUPPORT_COUNT\nWEIGHT_LOCATION_DENSITY\nWEIGHT_CATEGORY_URGENCY"]

    style ENV fill:#FF6B35,color:#fff
    style PS fill:#4285F4,color:#fff
```

| Variabel | Tipe | Default | Wajib | Deskripsi |
|---|---|---|---|---|
| `APP_NAME` | `string` | `LaporKita AI Service` | Tidak | Nama aplikasi service |
| `APP_ENV` | `string` | `development` | Tidak | Environment mode (`development` / `production`) |
| `PORT` | `int` | `8000` | Tidak | Port listen server |
| `HOST` | `string` | `0.0.0.0` | Tidak | Host listen server |
| `LOG_LEVEL` | `string` | `INFO` | Tidak | Tingkat logging (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| **— Model Paths —** | | | | |
| `CLASSIFICATION_MODEL_PATH` | `string` | `models/yolov11-cls-laporkita.pt` | **Ya** | Path ke file weights YOLOv11 |
| `XGBOOST_MODEL_PATH` | `string` | `models/xgboost-flood-risk.json` | **Ya** | Path ke file model XGBoost |
| **— DeepSeek LLM (Primary) —** | | | | |
| `DEEPSEEK_API_KEY` | `string` | `""` | **Ya** | API Key DeepSeek (dari [DeepSeek Platform](https://platform.deepseek.com)) |
| `DEEPSEEK_BASE_URL` | `string` | `https://api.deepseek.com` | Tidak | Base URL endpoint DeepSeek API |
| `DEEPSEEK_MODEL_NAME` | `string` | `deepseek-chat` | Tidak | Identifier model DeepSeek (default: `deepseek-chat`) |
| **— Gemini LLM (Optional Fallback) —** | | | | |
| `GEMINI_API_KEY` | `string` | `""` | Tidak | API Key Google Gemini (opsional) |
| `GEMINI_MODEL_NAME` | `string` | `gemini-2.5-flash` | Tidak | Identifier model Gemini |
| **— AI Verification Thresholds —** | | | | |
| `AI_CONFIDENCE_THRESHOLD` | `float` | `0.6` | Tidak | Ambang batas minimum confidence untuk auto-approve (`Rules.md §1.2`) |
| **— Kota Malang Bounding Box —** | | | | |
| `MALANG_BBOX_MIN_LAT` | `float` | `-8.0500` | Tidak | Batas selatan wilayah pilot (Kota Malang) |
| `MALANG_BBOX_MAX_LAT` | `float` | `-7.9000` | Tidak | Batas utara wilayah pilot |
| `MALANG_BBOX_MIN_LON` | `float` | `112.5500` | Tidak | Batas barat wilayah pilot |
| `MALANG_BBOX_MAX_LON` | `float` | `112.7000` | Tidak | Batas timur wilayah pilot |
| **— Smart Priority Weights —** | | | | |
| `WEIGHT_DAMAGE_SEVERITY` | `float` | `0.35` | Tidak | Bobot keparahan kerusakan (`Rules.md §1.3`) |
| `WEIGHT_SUPPORT_COUNT` | `float` | `0.25` | Tidak | Bobot dukungan/upvote warga |
| `WEIGHT_LOCATION_DENSITY` | `float` | `0.20` | Tidak | Bobot kepadatan laporan di wilayah |
| `WEIGHT_CATEGORY_URGENCY` | `float` | `0.20` | Tidak | Bobot urgensi kategori fasilitas |

---

## 🔀 Routing & URL Mapping (Dual-Prefix)

Service mendaftarkan router secara **dual-prefix** untuk mendukung dua klien berbeda:

```mermaid
graph TD
    Request["Incoming Request"] --> DualRouter{"Dual-Prefix\nRouter"}

    DualRouter -->|"/v1/..."| Canonical["Canonical Prefix\nFormat: APIResponse envelope\nsuccess, data, error"]
    DualRouter -->|"/api/v1/..."| NestJS["NestJS Compat Prefix\nFormat: sesuai kontrak\nNestJS service masing-masing"]

    Canonical --> CanVerify["POST /v1/verify\nVerifyReportData"]
    Canonical --> CanRisk["POST /v1/predict-risk\nPredictRiskData"]
    Canonical --> CanZone["POST /v1/predict/zone-metrics\nPredictZoneMetricsData"]
    Canonical --> CanPolicy["POST /v1/policy-simulate\nPolicySimulateData"]
    Canonical --> Health["GET /health"]

    NestJS -->|"Didaftarkan PERTAMA\nprioritas menang"| NestVerifyFlat["POST /api/v1/verify\nFlat response\nVerifyReportNestJSData"]
    NestJS --> NestRisk["POST /api/v1/predict-risk\nEnvelope standard"]
    NestJS --> NestZone["POST /api/v1/predict/zone-metrics\nFlat response"]
    NestJS --> NestPolicy["POST /api/v1/policy-simulate\nEnvelope standard"]

    style NestVerifyFlat fill:#FFF8E1,stroke:#F9A825
    style Canonical fill:#E3F2FD,stroke:#1976D2
    style NestJS fill:#E8F5E9,stroke:#34A853
```

| Klien | URL Prefix | Format Response | Keterangan |
|---|---|---|---|
| **Canonical / Testing** | `/v1/...` | `{ success, data, error }` envelope standar | Untuk penggunaan langsung & testing |
| **NestJS Backend** | `/api/v1/...` | Sesuai kontrak masing-masing service | Terintegrasi dengan `backend-laporkita` |

> **Catatan Registrasi `/api/v1/verify`:** `verify_compat_router` didaftarkan **pertama** dan mengembalikan response **flat** tanpa envelope — menang karena prioritas registrasi router di FastAPI.

---

## 📡 Dokumentasi Lengkap Semua Endpoint

### 1. `GET /health`

Mengecek status kesehatan server dan kesiapan operasional semua model ML di memori.

- **URL:** `GET http://localhost:8000/health`
- **Auth:** Tidak diperlukan
- **Response Model:** `APIResponse[HealthStatusData]`

```mermaid
stateDiagram-v2
    [*] --> CheckYOLO : GET /health
    CheckYOLO --> CheckXGB : YOLO loaded?
    CheckXGB --> CheckGemini : XGBoost loaded?
    CheckGemini --> Decision : API key configured?
    Decision --> OK : All true
    Decision --> Degraded : Any false
    OK --> [*] : HTTP 200 status ok
    Degraded --> [*] : HTTP 200 status degraded
```

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

### 2. `GET /demo` & `GET /` — Interactive Web Console

Antarmuka pengujian visual web interaktif (*glassmorphism UI*) untuk menguji verifikasi citra YOLOv11-cls, prediksi risiko XGBoost, dan simulasi kebijakan DeepSeek LLM secara langsung di browser tanpa Postman.

- **URL:** `GET http://localhost:8000/demo` atau `GET http://localhost:8000/`
- **Fitur Utama:**
  - 🕳️ **1-Click Presets Citra:** Uji cepat 5 kategori fasilitas publik dengan citra tersemat.
  - 🗺️ **GPS Malang Presets:** Alun-Alun, Suhat, Ijen, dan Luar Malang (Uji Fail-Closed).
  - 📊 **Visual Gauge & Breakdown:** Distribusi probabilitas Softmax, skor *Damage Severity*, dan dekomposisi *Smart Priority*.
  - 🤖 **DeepSeek Policy Sandbox:** Skenario cepat anggaran Kota Malang dengan output narasi eksekutif dan kartu metrik proyeksi.
- **Content-Type:** `text/html; charset=utf-8`

---

### 3. `POST /v1/verify` — Canonical (envelope)

Verifikasi laporan foto kerusakan fasilitas publik warga menggunakan YOLOv11-cls.

- **URL (Canonical):** `POST http://localhost:8000/v1/verify`
- **URL (Via NestJS proxy):** `POST http://localhost:8000/api/v1/verify` *(format berbeda, lihat endpoint #3)*
- **Content-Type:** `application/json`
- **Response Model:** `APIResponse[VerifyReportData]`

#### Pipeline Verifikasi (Rules.md §1.2):

```mermaid
flowchart LR
    S1["1️⃣ Validasi GPS\nMalang BBox Check"]
    S2["2️⃣ Validasi Timestamp\nAnomali Detection"]
    S3["3️⃣ Inferensi YOLOv11\n5 kelas klasifikasi"]
    S4["4️⃣ Decision Rule\nconfidence >= threshold"]
    S5["5️⃣ Hitung urgency_score\nSmart Priority Formula"]

    S1 --> S2 --> S3 --> S4 --> S5
```

1. **Validasi GPS** → Koordinat dalam Bounding Box Kota Malang
2. **Validasi Timestamp** → Timestamp tidak anomali (terlalu lampau / masa depan)
3. **Inferensi YOLOv11-cls** → Klasifikasi ke 5 kelas
4. **Decision Rule:**
   - `confidence >= 0.6` **DAN** GPS valid **DAN** Timestamp valid → `is_valid: true, needs_manual_review: false`
   - Salah satu gagal → `is_valid: false, needs_manual_review: true` *(masuk antrean review operator, **bukan ditolak**)*
5. **Hitung Smart Priority** `urgency_score` (Rules.md §1.3)

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

#### Formula `urgency_score` (Smart Priority — Rules.md §1.3):

```
urgency_score = (0.35 × damage_severity)
              + (0.25 × support_count_normalized)
              + (0.20 × location_density_factor)
              + (0.20 × category_urgency_weight)
```

Nilai `category_urgency_weight` per kategori:

| Kategori | Bobot Urgensi | Alasan |
|---|---|---|
| 🔴 Jalan Berlubang | **0.90** | Risiko kecelakaan langsung |
| 🟠 Drainase | **0.85** | Risiko banjir dan genangan |
| 🟡 Rambu Lalu Lintas | **0.80** | Risiko keselamatan lalu lintas |
| 🟢 Lampu Jalan | **0.70** | Risiko keamanan malam hari |
| 🔵 Trotoar | **0.65** | Risiko pejalan kaki |

---

### 3. `POST /api/v1/verify` — NestJS Compat (flat)

Endpoint kompatibilitas khusus untuk `backend-laporkita` (NestJS). Menggunakan **pipeline inferensi yang sama** dengan endpoint canonical, namun mengembalikan response **flat** (tanpa wrapper envelope) sesuai kontrak `ai-verification.service.js`.

- **URL:** `POST http://localhost:8000/api/v1/verify`
- **Content-Type:** `application/json`
- **Response Model:** `VerifyReportNestJSData` (flat, tanpa `success`/`error` wrapper)

#### Request Body:
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

Memprediksi probabilitas risiko genangan air dan tingkat stres wilayah menggunakan XGBoost baseline.

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
| `report_density` | `int` | Tidak (default: 0) | `>= 0` | Jumlah laporan aktif di zona |
| `weather_context.rainfall_mm` | `float` | Tidak (default: 0.0) | `>= 0.0` | Curah hujan dalam milimeter |
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

```mermaid
graph LR
    Prob["flood_risk_probability\n0.0 sampai 1.0"]
    Low["🟢 LOW\n< 0.40\nPemantauan rutin"]
    Medium["🟡 MEDIUM\n0.40 sampai 0.70\nSiaga pompa dan drainase"]
    High["🔴 HIGH\n> 0.70\nWaspada mobilisasi DPUPR + Dishub"]

    Prob --> Low
    Prob --> Medium
    Prob --> High

    style Low fill:#E8F5E9,stroke:#34A853
    style Medium fill:#FFF8E1,stroke:#F9A825
    style High fill:#FFEBEE,stroke:#C62828
```

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

### 7. `POST /v1/policy-simulate`

Mensimulasikan skenario intervensi kebijakan pemerintah kota menggunakan DeepSeek API (`deepseek-chat`) dengan output JSON terstruktur yang divalidasi oleh Pydantic serta diproteksi dari injeksi teks.

- **URL (Canonical):** `POST http://localhost:8000/v1/policy-simulate`
- **URL (NestJS):** `POST http://localhost:8000/api/v1/policy-simulate`
- **Content-Type:** `application/json`
- **Response Model:** `APIResponse[PolicySimulateData]`
- **Timeout:** 20 detik (DeepSeek API)

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
    "model_used": "deepseek-chat",
    "_placeholder": false
  },
  "error": null
}
```

#### Response Error (HTTP 503 — API Key Belum Dikonfigurasi):
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "LLM_KEY_NOT_CONFIGURED",
    "message": "DeepSeek / LLM API Key belum dikonfigurasi di environment server."
  }
}
```

#### Response Error (HTTP 504 — DeepSeek Timeout):
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "LLM_TIMEOUT",
    "message": "Permintaan simulasi kebijakan ke LLM API melebihi batas waktu (20 detik)."
  }
}
```

#### Response Error (HTTP 502 — Format Tidak Valid dari LLM):
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "LLM_INVALID_RESPONSE",
    "message": "Output dari LLM API bukan merupakan format JSON yang valid."
  }
}
---

## 📐 Format Response Envelope Standar

Semua endpoint canonical (`/v1/...`) menggunakan format response envelope standar (`Rules.md §3`):

**Success:**
```json
{
  "success": true,
  "data": { "..." },
  "error": null
}
```

**Error:**
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Deskripsi error yang jelas",
    "details": []
  }
}
```

> **Catatan:** Endpoint NestJS Compat (`/api/v1/verify`, `/v1/predict/zone-metrics`) mengembalikan format **flat** tanpa envelope sesuai kontrak NestJS.

---

## 🚨 Error Codes & HTTP Status Reference

```mermaid
graph TD
    Request["Incoming Request"] --> Validate{"Pydantic\nValidation"}
    Validate -->|"Field missing atau invalid"| E422V["422 VALIDATION_ERROR"]
    Validate -->|"Image corrupt / SSRF Blocked"| E422I["422 INVALID_IMAGE"]
    Validate -->|"Valid"| Process{"Process Inference"}
    Process -->|"Model .pt/.json hilang"| E503M["503 MODEL_NOT_AVAILABLE\nFail-Closed"]
    Process -->|"API Key LLM belum diset"| E503K["503 LLM_KEY_NOT_CONFIGURED"]
    Process -->|"LLM JSON invalid"| E502["502 LLM_INVALID_RESPONSE"]
    Process -->|"LLM timeout > 20s"| E504["504 LLM_TIMEOUT"]
    Process -->|"Unknown exception"| E500["500 INTERNAL_SERVER_ERROR"]
    Process -->|"Endpoint not found"| E404["404 HTTP_404"]
    Process -->|"Success"| E200["200 OK"]

    style E200 fill:#E8F5E9,stroke:#34A853,color:#1B5E20
    style E422V fill:#FFF8E1,stroke:#F9A825,color:#F57F17
    style E422I fill:#FFF8E1,stroke:#F9A825,color:#F57F17
    style E503M fill:#FFEBEE,stroke:#C62828,color:#B71C1C
    style E503K fill:#FFEBEE,stroke:#C62828,color:#B71C1C
    style E502 fill:#FFEBEE,stroke:#C62828,color:#B71C1C
    style E504 fill:#FFEBEE,stroke:#C62828,color:#B71C1C
    style E500 fill:#FFEBEE,stroke:#C62828,color:#B71C1C
    style E404 fill:#F3E5F5,stroke:#7B1FA2,color:#4A148C
```

| HTTP Status | Error Code | Trigger |
|---|---|---|
| `200` | — | Sukses memproses inferensi |
| `422` | `VALIDATION_ERROR` | Field wajib tidak ada, rentang nilai salah, atau format tidak valid |
| `422` | `INVALID_IMAGE` | Gambar tidak dapat dibaca (corrupt, base64 invalid, atau diblokir SSRF) |
| `503` | `MODEL_NOT_AVAILABLE` | Bobot model YOLOv11/XGBoost belum dimuat (kebijakan Fail-Closed MOCK-1) |
| `503` | `LLM_KEY_NOT_CONFIGURED` | API Key DeepSeek belum diset di `.env` (kebijakan LAT-POL) |
| `502` | `LLM_INVALID_RESPONSE` | DeepSeek mengembalikan format yang tidak dapat divalidasi skema Pydantic |
| `504` | `LLM_TIMEOUT` | DeepSeek API tidak merespons dalam batas waktu 20 detik |
| `500` | `INTERNAL_SERVER_ERROR` | Error tidak terduga di sisi server |
| `404` | `HTTP_404` | Endpoint tidak ditemukan |

---

## 📊 Ringkasan Dataset Publik (5 Kategori)

Rincian lengkap, URL verifikasi, dan analisis domain gap didokumentasikan di [`dataset_report.md`](dataset_report.md).

```mermaid
pie title Distribusi Dataset Training (1.796 Gambar)
    "Drainase (381)" : 381
    "Trotoar (420)" : 420
    "Jalan Berlubang (340)" : 340
    "Lampu Jalan (312)" : 312
    "Rambu Lalu Lintas (343)" : 343
```

| Kategori LaporKita | Dataset Publik | Sumber | Lisensi | Clean | Train (70%) | Val (15%) | Test (15%) |
|---|---|---|---|---|---|---|---|
| **🔴 Jalan Berlubang** | Roboflow Pothole / RDD2022 | [HuggingFace](https://huggingface.co/datasets/keremberke/pothole-segmentation) | CC BY 4.0 | **486** | 340 | 72 | 74 |
| **🔵 Trotoar** | METU Concrete Crack Images (CCIC) | [Mendeley Data](https://data.mendeley.com/datasets/5y9wdsg2zt/2) | CC BY 4.0 | **600** | 420 | 90 | 90 |
| **🟡 Rambu Lalu Lintas** | German Traffic Sign Detection (GTSDB) | [HuggingFace](https://huggingface.co/datasets/keremberke/german-traffic-sign-detection) | CC BY 4.0 | **491** | 343 | 73 | 75 |
| **🟠 Lampu Jalan** | Team16 Street Light Dataset | [GitHub](https://github.com/Team16Project/Street-Light-Dataset) | MIT | **447** | 312 | 67 | 68 |
| **🟤 Drainase** | Manhole Covers & Storm Drains | [HuggingFace](https://huggingface.co/datasets/delima87/manhole_covers_dataset) | CC BY 4.0 | **545** | 381 | 81 | 83 |
| **TOTAL** | | | | **2.569** | **1.796** | **383** | **390** |

**Stratified Split 70 / 15 / 15:**

```mermaid
graph LR
    Raw["2.569 Gambar\nRaw Dataset"] -->|"Cleaning & Dedup"| Clean["2.569 Gambar Clean"]
    Clean -->|"70%"| Train["Train Set\n1.796 gambar"]
    Clean -->|"15%"| Val["Val Set\n383 gambar\nearly stopping"]
    Clean -->|"15%"| Test["Test Set\n390 gambar\nheld-out evaluasi final"]

    style Train fill:#E3F2FD,stroke:#1976D2
    style Val fill:#FFF8E1,stroke:#F9A825
    style Test fill:#E8F5E9,stroke:#34A853
```

---

## 📈 Metrik Evaluasi Model Riil

### A. YOLOv11-cls Computer Vision (Test Set: 390 Citra, Leak-Free Held-Out)

*Evaluasi dijalankan pada held-out test set independen bebas kebocoran (`dataset/test/`) paska-resolusi LEAK-1.*

| Metrik | Nilai |
|---|---|
| **Top-1 Accuracy** | **99.23%** (387/390 benar) |
| **Macro Average F1-Score** | **99.23%** |
| **Kecepatan Inferensi (MPS GPU)** | **~0.6–2.9 ms / citra** (API End-to-End: ~30–115ms) |
| **Model Architecture** | `yolo11n-cls` (Nano Classifier) |
| **Training Data** | 1.796 citra (70% leak-free group split) |
| **Pretrained From** | ImageNet (Transfer Learning) |

**Per-Class Precision / Recall / F1:**

| Kategori Fasilitas | Precision | Recall | F1-Score | Support (Test) |
|---|---|---|---|---|
| **Drainase** | 0.9762 | 0.9880 | **0.9820** | 83 |
| **Jalan Berlubang** | 1.0000 | 0.9730 | **0.9863** | 74 |
| **Lampu Jalan** | 1.0000 | 1.0000 | **1.0000** | 68 |
| **Rambu Lalu Lintas** | 0.9868 | 1.0000 | **0.9934** | 75 |
| **Trotoar** | 1.0000 | 1.0000 | **1.0000** | 90 |
| **Macro Average** | **0.9926** | **0.9922** | **0.9923** | **390** |

```mermaid
xychart-beta
    title "Per-Class F1-Score YOLOv11-cls (%)"
    x-axis ["Drainase", "Jalan Berlubang", "Lampu Jalan", "Rambu", "Trotoar"]
    y-axis "F1-Score (%)" 97 --> 100.5
    bar [98.20, 98.63, 100.00, 99.34, 100.00]
```

*Laporan evaluasi mendalam (confusion matrix, per-class error analysis, training curves) tersedia di [`training_report.md`](training_report.md) dan laporan batasan di [`LIMITATIONS.md`](LIMITATIONS.md).*

---

### B. XGBoost Risk Prediction (Test Set: 1.200 Sampel Sintetis — Baseline)

*Evaluasi pada 20% held-out dari total 6.000 sampel dataset sintetis hidrologi perkotaan (Self-Consistency Baseline).*

| Metrik | Nilai | Interpretasi |
|---|---|---|
| **R² Score (Sintetis)** | **0.9635** | Model merefleksikan 96.35% variansi formula sintetis baseline |
| **RMSE** | **0.0490** | Rata-rata deviasi probabilitas ±4.90% |
| **MAE** | **0.0369** | Rata-rata deviasi probabilitas ±3.69% |
| **Model Architecture** | `XGBRegressor` | `n_estimators=300, max_depth=6, learning_rate=0.05` |
| **Training Data** | 4.800 sampel sintetis | 80% dari 6.000 sampel hidrologi sintetis |

```mermaid
xychart-beta
    title "Performa XGBoost Risk Predictor"
    x-axis ["R2 Score", "Precision (1-RMSE)", "Accuracy (1-MAE)"]
    y-axis "Score" 0.8 --> 1.05
    bar [0.9635, 0.9510, 0.9631]
```

---

## 🏗️ Arsitektur Decision Log

Keputusan teknis utama yang dibuat selama pengembangan:

```mermaid
timeline
    title Fase Pengembangan LaporKita AI Service
    section Fase 1 - Foundation
        Desain microservice : FastAPI + Dual-prefix routing
        Pydantic Settings : env-based configuration system
    section Fase 2 - Dataset
        Kurasi 5 dataset publik : 2.569 gambar CC BY 4.0 + MIT
        Stratified 70/15/15 split : scripts/prepare_dataset.py
    section Fase 3 - Computer Vision
        Rebuild dataset dHash <=8 : scripts/rebuild_clean_dataset.py (LEAK-1 fix)
        Training YOLOv11n-cls : Transfer learning + 180° rotation augmentation
        Evaluasi test set : 99.23% Top-1 Accuracy (387/390 benar)
    section Fase 4 - Risk Prediction
        Sintesis 6.000 sampel hidrologi : generate_synthetic_zone_data.py
        Training XGBoost : R2 = 0.9635, RMSE = 0.0490
    section Fase 5 - LLM Integration
        Migrasi ke DeepSeek API : deepseek-chat via httpx client
        Prompt Injection Guard : Sanitasi keyword & skema validasi Pydantic
    section Fase 6 - Testing & Security
        32 unit tests passing : pytest asyncio (Health, Verification, Prediction, Security, Policy)
        SSRF & Size Protection : Blokir IP privat/metadata, limit 8MB, fail-closed policy
        Interactive Web Console : index.html at GET /demo & GET /
```

| Keputusan | Pilihan | Alternatif Dipertimbangkan | Alasan |
|---|---|---|---|
| **Model klasifikasi** | `yolo11n-cls` (Nano) | CLIP, MobileNet, ResNet50 | Ekosistem Ultralytics mature, inference ~2ms, mudah di-retrain dengan foto lokal |
| **Deployment model** | Weights di-copy ke Docker image | Volume mount dari host | Container benar-benar mandiri (*self-contained*), tidak ada external dependency saat runtime |
| **Dockerfile** | Single-stage CPU PyTorch | Multi-stage build | Multi-stage gagal karena Docker Desktop memory limit saat download CUDA packages (>1GB); CPU cukup untuk inference |
| **Dataset strategi** | Public datasets + proxy visual | Scraping foto laporan lokal | Zero foto lapangan Kota Malang tersedia; proxy public datasets memungkinkan training langsung dijalankan |
| **Data historis XGBoost** | Sintetis (aturan hidrologi) | BMKG API + laporan DPUPR | Data historis riil belum tersedia; synthetic data cukup untuk demo dengan pola prediksi yang masuk akal |
| **Dual-prefix routing** | `/v1/...` + `/api/v1/...` | Satu prefix saja | NestJS backend memanggil `/api/v1/...`; prefix canonical `/v1/...` dipertahankan untuk backward compatibility dan testing |
| **NestJS compat response** | Flat schema terpisah (`VerifyReportNestJSData`) | Transform di NestJS | Menghindari parsing ganda di NestJS layer; AI Service bertanggung jawab penuh atas format yang dikonsumsinya |

---

## ⚠️ Disclaimer & Known Limitations (Produksi)

Untuk keterbukaan teknis (*technical honesty*) sebelum deployment ke production sesungguhnya:

### 1. Domain Shift — Zero Field Validation Kota Malang

```mermaid
graph LR
    TrainData["Training Data\nDataset Publik Internasional"]
    FieldData["Field Data\nFoto Warga Malang"]
    Gap["⚠️ DOMAIN GAP\nSudut foto tidak ideal\nKamera resolusi rendah\nPencahayaan ekstrem\nTampilan fisik berbeda"]

    TrainData -->|"99.23% Test Acc"| ModelPerf["Model Performance\npada test set publik"]
    FieldData --> Gap --> ActualPerf["Performa Aktual\nBELUM DIVALIDASI"]
    ModelPerf -.->|"Mungkin berbeda signifikan"| ActualPerf

    style Gap fill:#FFEBEE,stroke:#C62828,color:#B71C1C
    style ActualPerf fill:#FFF8E1,stroke:#F9A825,color:#F57F17
```

Model YOLOv11 dievaluasi pada held-out test set dari dataset publik bebas kebocoran (akurasi **99.23%**). **Belum ada validasi dengan foto lapangan warga asli Kota Malang.**

> **Rekomendasi:** Lakukan labeling **200–500 foto lapangan warga Malang per kategori** dan fine-tune model sebelum production launch. Dokumentasi lengkap limitasi teknis tersedia di [`LIMITATIONS.md`](LIMITATIONS.md).

---

### 2. Kategori Proxy Visual

| Kategori | Dataset yang Digunakan | Gap Representasi |
|---|---|---|
| **Trotoar** | Concrete Crack Images (pelat beton) | Belum mencakup paving block warna, trotoar tanah, kanstin rusak |
| **Drainase** | Manhole covers & grill saluran air | Belum mencakup parit terbuka, selokan batu bata, saluran lahan sawah |
| **Rambu Lalu Lintas** | GTSDB (standar Eropa) | Piktogram minor berbeda dari rambu Dishub/Kemenhub RI |

---

### 3. Data Historis XGBoost Sintetis

Model XGBoost dilatih pada **6.000 sampel sintetis** yang dihasilkan berdasarkan aturan hidrologi perkotaan logistik (`scripts/generate_synthetic_zone_data.py`). Dataset ini **BUKAN data observasi riil**.

> **WAJIB di-retrain** dengan data historis riil (deret waktu curah hujan stasiun BMKG Karangploso + log penanganan fisik DPUPR Kota Malang) sebelum digunakan untuk pengambilan keputusan anggaran atau kebijakan publik yang sesungguhnya.

---

### 4. Metrik `damage_severity` sebagai Proxy

Nilai `damage_severity` (0.0–1.0) adalah **estimasi terkalibrasi** dari confidence model klasifikasi dan bobot urgensi kelas per kategori. Ini **bukan pengukuran langsung** luas fisik kerusakan per meter persegi. Untuk kuantifikasi kerusakan yang akurat, diperlukan model segmentasi (SAM/Mask R-CNN) atau survei fisik lapangan.

---

<div align="center">

**LaporKita AI Service** — Powered by YOLOv11, XGBoost & DeepSeek LLM

*Built for Kota Malang · MAGEITS Competition 2026*

</div>
