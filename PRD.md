# Product Requirements Document (PRD)
## LaporKita — City Intelligence Platform untuk Kota yang Lebih Responsif

**Versi:** 2.0 (Full Stack — Frontend & Backend)
**Tanggal:** 21 Agustus 2026
**Tim:** Saya Akan Lawan — SMK Telkom Malang

---

## 1. Ringkasan Produk

LaporKita adalah platform pelaporan fasilitas umum berbasis AI dengan konsep **"From Report to Resolve"**, diimplementasikan melalui **Digital Accountability Loop**:

```
Report → AI Verification → Smart Priority → Government Action
       → Public Tracking → Citizen Validation → Resolve
```

Produk terdiri dari:
- **Citizen App (B2C)** — warga melapor kerusakan fasilitas umum via foto, memantau progres, memberi dukungan.
- **Command Center (B2G)** — operator pemerintah (DPUPR, Dishub, Diskominfo) memverifikasi, memprioritaskan, dan menindaklanjuti laporan.
- **Backend Platform** — mengorkestrasi data, AI pipeline (Computer Vision, prediksi, LLM), dan integrasi peta.

---

## 2. Tujuan Produk

1. Menyediakan kanal pelaporan yang cepat (3-tap) dan minim friksi bagi warga.
2. Mengotomatisasi verifikasi & klasifikasi laporan menggunakan Computer Vision agar mengurangi beban verifikasi manual.
3. Memberi pemerintah alat prioritas berbasis data (tingkat kerusakan, lokasi, dukungan warga) untuk pengambilan keputusan.
4. Menciptakan transparansi penuh melalui Public Tracking dan visibilitas laporan di peta publik.
5. Membangun basis data historis fasilitas umum sebagai dasar kebijakan (Policy Simulator).

---

## 3. Sasaran Pengguna

| Role | Deskripsi | Akses |
|---|---|---|
| `citizen` | Warga umum | Citizen App |
| `operator` | Staf dinas (DPUPR/Dishub/Diskominfo) | Command Center |
| `policy_maker` | Kepala dinas/pengambil kebijakan | Command Center + Policy Simulator |
| `admin` | Admin sistem | Command Center + panel manajemen user/kategori |

---

## 4. Ruang Lingkup Fungsional

### 4.1 Modul Citizen App (B2C)
- Registrasi/Login (email/no. HP + OTP atau sosial login)
- Citizen Vision: kamera + deteksi objek on-device (real-time preview)
- Submit laporan (foto, lokasi GPS otomatis, kategori hasil deteksi AI, deskripsi otomatis)
- Peta Interaktif (Urban Emotion Map) dengan zona warna & pin laporan
- Detail laporan: timeline status, dukungan (upvote), komentar
- Citizen Validation: konfirmasi laporan selesai diperbaiki
- Route Alert: notifikasi kontekstual saat mendekati titik kerusakan
- Profil & Poin Kontribusi

### 4.2 Modul Command Center (B2G)
- Dashboard: Urban Health Score, Prioritas Prediksi Harian, ringkasan laporan
- Manajemen laporan: filter, verifikasi manual (override AI jika perlu), ubah status, tugaskan ke petugas lapangan
- Peta & heatmap zona
- Policy Simulator: input prompt → hasil simulasi kebijakan (LLM-generated)
- Manajemen kategori fasilitas & instansi terkait
- Laporan analitik (tren, backlog, rata-rata waktu penyelesaian)

### 4.3 Modul Backend / Platform
- AI Verification Service (Computer Vision — validasi foto, klasifikasi jenis kerusakan)
- Smart Priority Engine (skoring berdasarkan tingkat kerusakan, lokasi, community support)
- Prediction Service (XGBoost — prediksi risiko/cuaca/kemacetan terkait fasilitas)
- Policy Simulator Service (Gemini — narasi & proyeksi kebijakan)
- Notification Service (push notification + geofencing Route Alert)
- Maps Service (Geocoding, zona, pin publik via Google Maps Platform)
- Auth & User Management Service
- Reporting/Analytics Service

---

## 5. User Stories Utama

| ID | Sebagai | Saya ingin | Agar |
|---|---|---|---|
| US-01 | Warga | Melapor kerusakan hanya dengan foto | Prosesnya cepat tanpa mengetik manual |
| US-02 | Warga | Melihat status laporan saya | Saya tahu progres penanganannya |
| US-03 | Warga | Mendukung laporan orang lain | Membantu prioritas laporan penting |
| US-04 | Warga | Mendapat notifikasi rute | Bisa menghindari/mengantisipasi jalan rusak |
| US-05 | Warga | Mengonfirmasi laporan telah selesai diperbaiki | Data akurat sesuai kondisi lapangan |
| US-06 | Operator | Melihat daftar prioritas harian | Fokus menangani laporan paling mendesak dulu |
| US-07 | Operator | Memverifikasi & mengubah status laporan | Alur kerja penanganan tercatat rapi |
| US-08 | Policy Maker | Menjalankan simulasi kebijakan | Mengambil keputusan tata ruang berbasis data |
| US-09 | Admin | Mengelola kategori & instansi | Sistem tetap terorganisir saat berkembang |

---

## 6. Alur Utama (Core Flow)

### 6.1 Alur Pelaporan Warga
1. Warga buka Citizen Vision → kamera aktif, GPS aktif.
2. On-device model (YOLOv11/TFLite) mendeteksi objek secara real-time → menampilkan label & confidence.
3. Warga potret → sistem isi otomatis: kategori, lokasi (reverse geocoded), timestamp.
4. Warga kirim → laporan berstatus `pending_verification`.
5. Backend menjalankan **AI Verification** (ulang, server-side, lebih akurat) → validasi foto/GPS/metadata.
6. Jika valid → status `verified`, masuk **Smart Priority Engine** → mendapat skor prioritas.
7. Laporan tampil sebagai pin di peta publik.
8. Operator menindaklanjuti → status berubah bertahap: `assigned` → `in_progress` → `completed`.
9. Warga/pelapor melakukan **Citizen Validation** → status akhir `resolved` atau `disputed` (jika tidak sesuai).

### 6.2 Alur Smart Priority
Skor prioritas = f(tingkat kerusakan dari AI, jumlah dukungan warga, lokasi/kepadatan, riwayat laporan serupa di area).

### 6.3 Alur Route Alert
Backend menyimpan titik laporan `verified` → saat aplikasi warga mendeteksi pergerakan mendekati radius tertentu dari titik tersebut → kirim push notification kontekstual.

---

## 7. Kebutuhan Non-Fungsional

| Kategori | Kebutuhan |
|---|---|
| Performa | API response < 500ms (non-AI endpoint); AI verification < 5 detik async |
| Skalabilitas | Backend microservice-ready (gateway + service terpisah untuk AI) |
| Keamanan | JWT auth, role-based access control (RBAC), rate limiting endpoint publik |
| Ketersediaan | Target uptime 99% untuk MVP pilot |
| Privasi Data | Foto & lokasi warga tidak dipublikasikan bersama identitas pribadi |
| Auditability | Semua perubahan status laporan tercatat di histori (audit trail) |

---

## 8. Metrik Keberhasilan (KPI)

| Metrik | Target Tahun 1 |
|---|---|
| Pengguna aktif (SOM) | 15.000–20.000 |
| Rata-rata waktu verifikasi AI | < 5 detik |
| Rata-rata waktu penyelesaian laporan | Menurun dari baseline manual |
| Tingkat validasi warga (citizen validation rate) | > 60% laporan selesai divalidasi warga |
| Akurasi klasifikasi AI | > 85% |

---

## 9. Out of Scope (MVP)
- Ekspansi multi-kota (fokus pilot Kota Malang)
- Pembayaran/insentif finansial (poin kontribusi bersifat gamifikasi non-moneter)
- Integrasi langsung ke sistem internal existing tiap dinas (API-level saja untuk MVP)

---

## 10. Roadmap Bertahap

1. **MVP (Pilot Malang):** Citizen App inti + Command Center dasar + AI Verification + Smart Priority sederhana
2. **Fase 2:** Route Alert, Policy Simulator, analitik lanjutan
3. **Fase 3:** Ekspansi ke Malang Raya & kota lain Jawa Timur