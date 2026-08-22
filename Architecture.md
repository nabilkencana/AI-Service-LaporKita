# System Architecture — LaporKita

---

## 1. High-Level Architecture

```
┌─────────────────────────────┐
│        Client Layer         │
│   Flutter Mobile App (.apk) │
│  - Citizen App (B2C)        │
│  - Command Center (B2G)     │
│  - On-device: YOLOv11/TFLite│
└──────────────┬───────────────┘
               │ REST/HTTPS (JWT)
┌──────────────▼───────────────┐
│      Backend Gateway         │
│   NestJS REST API (TS)       │
│  - Auth & RBAC                │
│  - Report Controller          │
│  - Notification Controller    │
│  - Orkestrasi ke Data & AI    │
└──────┬───────────────┬────────┘
       │               │
┌──────▼──────┐  ┌─────▼─────────────────┐
│ Data Layer  │  │      AI Layer          │
│ PostgreSQL  │  │ - YOLOv11 (verifikasi  │
│ + Prisma    │  │   server-side, opsional│
│ (Supabase)  │  │   re-check)            │
│             │  │ - XGBoost (prediksi)   │
│             │  │ - Gemini 2.5 (narasi/  │
│             │  │   policy simulator)    │
└─────────────┘  └────────────────────────┘
       │
┌──────▼───────────────────────┐
│  External Services            │
│  - Google Maps Platform       │
│    (Maps SDK, Geocoding API)  │
│  - BMKG Weather API            │
│  - FCM (Push Notification)     │
└────────────────────────────────┘
```

---

## 2. Arsitektur Frontend

### 2.1 Layered Structure (Flutter)
```
lib/
├── main.dart
├── core/
│   ├── network/        # Dio client, interceptors (auth token, retry)
│   ├── theme/           # Design tokens (warna, tipografi dari Design System)
│   ├── constants/
│   └── utils/
├── data/
│   ├── models/           # DTO (Report, User, Category, dll)
│   ├── repositories/     # Implementasi repository (panggil API)
│   └── datasources/      # remote (REST), local (cache/draft offline)
├── domain/
│   ├── entities/
│   └── usecases/         # business logic sisi client (mis. validasi form sebelum submit)
├── presentation/
│   ├── citizen/
│   │   ├── home/
│   │   ├── camera/        # Citizen Vision + integrasi TFLite
│   │   ├── map/
│   │   ├── report_detail/
│   │   └── profile/
│   ├── command_center/
│   │   ├── dashboard/
│   │   ├── report_management/
│   │   └── policy_simulator/
│   └── shared_widgets/    # ReportCard, StatusBadge, RadialProgress, dll
└── ai/
    └── tflite_service.dart  # wrapper inference on-device
```

### 2.2 Pola Arsitektur
- **Clean Architecture** (presentation → domain → data) agar business logic tidak bergantung langsung pada implementasi API.
- **State Management:** Riverpod/Bloc (per fitur) — rekomendasi Riverpod untuk skalabilitas & testability.
- **Offline-first parsial:** Draft laporan disimpan lokal (Hive/SQLite) saat tidak ada koneksi, auto-sync saat online.
- **Role-based routing:** Setelah login, `role` dari JWT menentukan initial route (Citizen App vs Command Center).

### 2.3 On-Device AI Flow
```
Camera Stream → Frame Preprocessing → TFLite Interpreter (YOLOv11)
→ Bounding Box + Label + Confidence → Overlay UI (real-time)
→ (saat shutter ditekan) → Freeze frame + hasil deteksi terakhir
→ dikirim sebagai HINT ke backend (bukan keputusan final)
```
> Prinsip penting: deteksi on-device bersifat **assistive** (mempercepat UX 3-tap), keputusan final validitas tetap di **AI Verification Service** backend agar konsisten & tidak mudah dimanipulasi client.

---

## 3. Arsitektur Backend

### 3.1 Modular Monolith (rekomendasi MVP) → Microservice-ready
Untuk MVP, backend dibangun sebagai **modular monolith** NestJS dengan modul terpisah secara logis, agar mudah dipecah jadi microservice saat skala bertambah:

```
src/
├── modules/
│   ├── auth/
│   ├── users/
│   ├── reports/
│   ├── categories/
│   ├── agencies/
│   ├── notifications/
│   ├── maps/                # wrapper Google Maps Platform
│   ├── ai-verification/     # panggil model CV (bisa internal atau service terpisah)
│   ├── smart-priority/      # scoring engine
│   ├── prediction/          # wrapper XGBoost service
│   ├── policy-simulator/    # wrapper Gemini API
│   └── points/              # gamifikasi kontribusi
├── common/
│   ├── guards/               # RBAC guard
│   ├── interceptors/
│   ├── filters/               # exception filter
│   └── decorators/
├── prisma/
│   └── schema.prisma
└── main.ts
```

### 3.2 AI Services — Deployment Terpisah
Model AI berat (YOLOv11 server-side re-check, XGBoost, Gemini call) sebaiknya dijalankan sebagai **service terpisah** (mis. Python FastAPI microservice untuk YOLOv11 & XGBoost) yang dipanggil NestJS via internal REST/gRPC, agar:
- Beban komputasi AI tidak mengganggu performa API utama.
- Model dapat di-scale independen (GPU instance terpisah bila diperlukan).

```
NestJS Gateway ──(internal REST)──> AI Service (FastAPI/Python)
                                     ├── YOLOv11 inference
                                     └── XGBoost prediction
NestJS Gateway ──(REST)──> Gemini API (Google, external)
```

### 3.3 Async Processing
Proses AI Verification & Prediction bersifat tidak instan → gunakan **job queue** (mis. BullMQ + Redis) agar:
1. Client submit laporan → dapat response cepat (`202 Accepted`, status `pending_verification`).
2. Worker memproses verifikasi AI di background.
3. Hasil di-update ke database → notifikasi dikirim ke client (push notification / polling / WebSocket).

```
POST /reports → [Queue: verify-report] → Worker (AI Verification)
             → Update status di DB → Emit event → Notification Service
```

---

## 4. Sequence Diagram: Submit Laporan (End-to-End)

```
Citizen App        NestJS Gateway       Queue/Worker      AI Service      DB           Notification
    │                    │                   │                │           │                │
    │  POST /reports     │                   │                │           │                │
    ├───────────────────>│                   │                │           │                │
    │                    │ save (pending)    │                │           │                │
    │                    ├───────────────────────────────────────────────>│                │
    │  202 Accepted      │                   │                │           │                │
    │<───────────────────┤                   │                │           │                │
    │                    │ enqueue verify-job│                │           │                │
    │                    ├──────────────────>│                │           │                │
    │                    │                   │ call inference │           │                │
    │                    │                   ├───────────────>│           │                │
    │                    │                   │  result         │           │                │
    │                    │                   │<───────────────┤           │                │
    │                    │                   │ update status   │           │                │
    │                    │                   ├─────────────────────────────>│              │
    │                    │                   │ trigger notif   │           │                │
    │                    │                   ├─────────────────────────────────────────────>│
    │  push notif "Laporan Anda telah diverifikasi"                                          │
    │<──────────────────────────────────────────────────────────────────────────────────────┤
```

---

## 5. Integrasi Google Maps Platform

| Kebutuhan | Layanan |
|---|---|
| Menampilkan peta & pin di mobile | Maps SDK for Flutter |
| Konversi koordinat GPS → alamat | Geocoding API (server-side, saat laporan diverifikasi) |
| Zona/heatmap custom | Di-render sendiri (polygon overlay) di atas Maps SDK, data dari `zones` table |

---

## 6. Deployment View (usulan MVP)

```
[Flutter App] ──HTTPS──> [API Gateway/Load Balancer]
                                │
                    ┌───────────┼────────────┐
              [NestJS x N]  [Worker x N]  [AI Service (Python)]
                    │             │              │
              [PostgreSQL/Supabase]  [Redis (Queue)]
```

- Containerization: Docker untuk semua service (NestJS, AI Service, Worker).
- CI/CD: pipeline terpisah untuk mobile (build .apk) dan backend (build & deploy image).
- Environment: `development`, `staging`, `production` (pilot Kota Malang).

---

## 7. Keamanan Arsitektur
- Semua komunikasi client-server via HTTPS + JWT (short-lived access token + refresh token).
- Guard RBAC di setiap endpoint (`citizen`, `operator`, `policy_maker`, `admin`).
- Rate limiting pada endpoint publik (submit laporan, komentar) untuk mencegah spam/flood.
- Validasi file upload (tipe, ukuran) sebelum masuk storage (Supabase Storage/S3-compatible).
- Audit trail otomatis via tabel `report_status_history` untuk setiap perubahan status.