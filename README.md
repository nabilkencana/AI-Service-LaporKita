# LaporKita — AI Service Microservice

Microservice Python FastAPI untuk platform **LaporKita**, menyediakan inference Computer Vision (klasifikasi kerusakan fasilitas), prediksi risiko berbasis Machine Learning (XGBoost), dan Policy Simulator berbasis LLM (Gemini 2.5).

Service ini dipanggil secara internal oleh Backend Gateway NestJS (`Architecture.md §3.2`).

---

## ⚠️ Limitasi Eksplisit & Catatan Demo

1. **Dataset Publik (Bukan Foto Asli Malang):** Seluruh model klasifikasi gambar dilatih dan dievaluasi menggunakan **dataset publik**. Belum ada sesi validasi dengan foto lapangan kondisi nyata Kota Malang pada demo ini. Metrik akurasi yang dilaporkan hanya berlaku untuk test set dataset publik.
2. **Data Historis Sintetis:** Data historis cuaca, traffic, dan densitas laporan untuk model XGBoost menggunakan **data sintetis** yang ditandai secara eksplisit.
3. **Response Placeholder (Fase 1):** Pada Fase 1, endpoint mengembalikan response dummy yang 100% valid sesuai skema Pydantic dan ditandai dengan field `"_placeholder": true`.

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

# 4. Jalankan unit test
pytest -v

# 5. Jalankan server FastAPI
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Dokumentasi OpenAPI/Swagger UI otomatis tersedia di: `http://localhost:8000/docs`

---

### 2. Menjalankan dengan Docker

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
| `POST` | `/v1/verify` | AI Verification klasifikasi gambar (5 kelas) & Smart Priority | 🟡 Kontrak Aktif (Mock) |
| `POST` | `/v1/predict-risk` | Prediksi probabilitas risiko genangan/infrastruktur (XGBoost) | 🟡 Kontrak Aktif (Mock) |
| `POST` | `/v1/policy-simulate` | Simulasi kebijakan perkotaan & proyeksi dampak (Gemini) | 🟡 Kontrak Aktif (Mock) |

---

## ⚙️ Variabel Konfigurasi (`.env`)

| Variabel | Tipe | Default | Deskripsi |
|---|---|---|---|
| `APP_NAME` | string | `LaporKita AI Service` | Nama aplikasi |
| `APP_ENV` | string | `development` | Environment (`development` / `production`) |
| `PORT` | int | `8000` | Port listen server |
| `LOG_LEVEL` | string | `INFO` | Level log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `AI_CONFIDENCE_THRESHOLD` | float | `0.6` | Threshold keyakinan minimum verifikasi otomatis (`Rules.md §1.2`) |
| `MALANG_BBOX_MIN_LAT` | float | `-8.0500` | Batas selatan Bounding Box Kota Malang |
| `MALANG_BBOX_MAX_LAT` | float | `-7.9000` | Batas utara Bounding Box Kota Malang |
| `MALANG_BBOX_MIN_LON` | float | `112.5500` | Batas barat Bounding Box Kota Malang |
| `MALANG_BBOX_MAX_LON` | float | `112.7000` | Batas timur Bounding Box Kota Malang |
| `WEIGHT_DAMAGE_SEVERITY` | float | `0.35` | Bobot keparahan kerusakan pada Smart Priority (`Rules.md §1.3`) |
| `WEIGHT_SUPPORT_COUNT` | float | `0.25` | Bobot dukungan/upvote warga pada Smart Priority |
| `WEIGHT_LOCATION_DENSITY` | float | `0.20` | Bobot densitas laporan sekitar pada Smart Priority |
| `WEIGHT_CATEGORY_URGENCY` | float | `0.20` | Bobot urgensi kategori pada Smart Priority |
| `GEMINI_API_KEY` | string | `""` | API key Google Gemini untuk Policy Simulator |
| `GEMINI_MODEL_NAME` | string | `gemini-2.5-flash` | Model Gemini yang digunakan |

---

## 🧪 Pengujian (Unit Test)

Jalankan test suite menggunakan pytest:

```bash
pytest -v
```

Hasil test mencakup:
- Validasi status kesehatan (`GET /health`)
- Uji skema input & output valid untuk 3 endpoint AI
- Uji validasi koordinat GPS dalam dan luar Kota Malang
- Uji perhitungan rumus Smart Priority scoring
- Uji serialisasi format error envelope untuk input invalid (422)
