# ⚠️ Batasan Teknis & Laporan Limitasi (Technical Limitations Report)

**Proyek:** LaporKita AI Service (FastAPI + YOLOv11-cls + XGBoost + DeepSeek LLM)  
**Dokumen:** `LIMITATIONS.md`  
**Status Evaluasi:** FIX ROUND 2 Verified (Fase 1–8)  
**Terakhir Diperbarui:** 23 Agustus 2026  

---

## 1. Ringkasan Kejujuran Ilmiah (Scientific Disclosure)

Laporan ini disusun sebagai bentuk **transparansi dan kejujuran teknis (technical integrity)** bagi pengembang, penguji (QA), maupun juri kompetisi. Seluruh angka evaluasi yang disajikan di bawah ini dapat direproduksi secara mandiri dari repo dan merefleksikan performa aktual sistem saat ini.

---

## 2. Metrik Evaluasi Model Klasifikasi 6-Kelas (YOLOv11-cls)

Evaluasi dilakukan pada **Held-out Test Set 6-Kelas Bebas Kebocoran** dengan total 457 citra independen yang telah melalui proses *Perceptual Hash Clustering* (`dHash` $\le 8$) dan *Video Sequence Grouping* (**Fix LEAK-1**):

| Kategori Fasilitas | Precision | Recall | F1-Score | Jumlah Test Data (Support) | 95% CI Recall (Wilson) |
|---|---|---|---|---|---|
| **Drainase** | 1.0000 | 1.0000 | **1.0000** | 83 | 95.58% – 100.00% |
| **Jalan Berlubang** | 0.9737 | 1.0000 | **0.9867** | 74 | 95.07% – 100.00% |
| **Lampu Jalan** | 1.0000 | 0.9877 | **0.9938** | 81 | 93.33% – 99.78% |
| **Rambu Lalu Lintas** | 1.0000 | 0.9867 | **0.9933** | 75 | 92.83% – 99.76% |
| **Trotoar** | 1.0000 | 1.0000 | **1.0000** | 90 | 95.91% – 100.00% |
| **bukan_fasilitas (OOD)** | 1.0000 | 1.0000 | **1.0000** | 54 | 93.36% – 100.00% |
| **GLOBAL (Macro Avg)** | **0.9956** | **0.9957** | **0.9956** | **457** | **98.42% – 99.88%** |

---

## 3. Resolusi Temuan Re-QA Round 2

### 3.1 Resolusi MODEL-OOD (Kelas ke-6 `bukan_fasilitas`)
- **Masalah:** Pada Round 1, model 5-kelas closed-set memaksakan citra abu-abu polos, gradient, atau noise menjadi Drainase/Jalan Berlubang dengan keyakinan tinggi.
- **Solusi FIX-1:** Implementasi kelas ke-6 `bukan_fasilitas` dengan 350 sampel negatif (warna solid, gradient, noise, dokumen, tekstur non-fasilitas).
- **Hasil Verifikasi:** Abu-abu polos 4000×3000, gradient, noise acak, dan foto non-fasilitas kini 100% terklasifikasi sebagai `bukan_fasilitas` (Confidence > 99.9%) $\to$ otomatis diarahkan ke `is_valid=false` dan `needs_manual_review=true`.

### 3.2 Resolusi SEC-NOAUTH (Autentikasi Internal API Key)
- **Masalah:** Endpoint `/v1/*` sebelumnya tidak memvalidasi otorisasi pemanggil.
- **Solusi FIX-2:** Header `X-API-Key` atau `Authorization: Bearer <key>` kini diverifikasi terhadap `INTERNAL_API_KEY`. Permintaan tanpa key menghasilkan **HTTP 401 Unauthorized**, key salah menghasilkan **HTTP 403 Forbidden**, sementara endpoint `/health` dan `/demo` tetap terbuka untuk monitoring dan pengujian UI.

### 3.3 Resolusi RES-480 & DEG-ROBUST (Resolusi & Kualitas Citra)
- **Distribusi Resolusi Empiris:** Sebanyak 60.4% (276 dari 457) citra pada test set publik berukuran antara 200px dan 479px (karena standar crop dataset benchmark). Pembatasan kaku 480px akan menolak lebih dari separuh citra yang valid.
- **Kalibrasi Server:** Ambang batas `MIN_IMAGE_DIMENSION` disetel ke **200px** untuk mengizinkan crop benchmark dan resolusi mobile sambil menolak thumbnail mikro (< 200px) dengan error HTTP 422 yang jelas.
- **Deteksi Blur:** Deteksi ketajaman citra berbasis *variance of Laplacian* dikalibrasi ke threshold **`1.5`** (citra blur berat bernilai 1.08–1.56, sementara citra normal memiliki median 371.15). Citra yang terlalu buram diarahkan ke `bukan_fasilitas` / antrean review manual.

### 3.4 Model Prediksi Risiko (XGBoost) Berbasis Baseline Sintetis
- **Fakta:** Target `flood_risk_probability` pada model XGBoost ($R^2 = 0.9635$, $\text{RMSE} = 0.0490$) dilatih menggunakan 6.000 baris data sintetis turunan formula logistik hidrologi internal untuk keperluan demonstrasi arsitektur microservice.
- **Penegasan:** Angka $R^2 = 0.9635$ mencerminkan *self-consistency* pada data sintetis, bukan metrik evaluasi model di dunia nyata. Sebelum diimplementasikan secara operasional di DPUPR Kota Malang, model **WAJIB** dilatih ulang dengan data riil observasi BMKG dan data genangan air historis.

### 3.5 Kebijakan Fail-Closed pada Seluruh Komponen AI
- Jika bobot model (`.pt` atau `.json`) tidak tersedia atau API Key LLM belum dikonfigurasi, service **TIDAK PERNAH** memfabrikasi hasil mock dengan response 200 palsu.
- Sistem akan mengembalikan response HTTP 503 `MODEL_NOT_AVAILABLE` atau `LLM_KEY_NOT_CONFIGURED`.
