# Rules & Standards — LaporKita
## Business Rules, Validation Rules, dan Coding Standards (Frontend & Backend)

---

## 1. Business Rules

### 1.1 Alur Status Laporan (State Machine)
Status hanya boleh berpindah sesuai urutan berikut (tidak boleh loncat/mundur, kecuali disebutkan):

```
pending_verification
   ├──> verified        (AI/operator menyatakan valid)
   └──> rejected         (AI/operator menyatakan tidak valid) [status akhir]

verified
   └──> assigned          (ditugaskan ke instansi/petugas)

assigned
   └──> in_progress        (petugas mulai menangani)

in_progress
   └──> completed           (petugas menandai selesai, wajib upload progress/completion photo)

completed
   ├──> resolved             (warga/citizen validation: sesuai)
   └──> disputed              (warga/citizen validation: tidak sesuai) → kembali ke in_progress
```

- Setiap perubahan status **wajib** tercatat di `report_status_history` (siapa, kapan, catatan).
- Status `rejected` bersifat final — laporan tidak dapat diproses ulang, namun boleh dilaporkan ulang oleh warga sebagai laporan baru.
- Status `disputed` mengembalikan laporan ke `in_progress` dan menaikkan urgency_score (prioritas ulang).
- **Catatan implementasi (F4-4):** Transisi `disputed` dicatat di `report_status_history` sebagai status efektif `in_progress` (karena `disputed` → `in_progress` terjadi otomatis dalam satu langkah), disertai note yang menjelaskan alasan dispute. Jejak bahwa laporan sempat di-dispute tetap tersedia lewat tabel `citizen_validations` (`is_valid=false`).

### 1.2 Aturan Verifikasi AI
- Laporan baru **selalu** melalui AI Verification server-side, meskipun sudah ada hasil deteksi on-device (on-device hanya hint UX).
- `ai_confidence_score` < 0.6 → otomatis diteruskan ke antrian **verifikasi manual operator**, tidak langsung ditolak.
- `ai_confidence_score` >= 0.6 → otomatis `verified`.
- Foto wajib memiliki metadata GPS & timestamp valid; jika salah satu tidak valid → laporan otomatis masuk verifikasi manual (tidak auto-reject).

### 1.3 Smart Priority Scoring
Formula dasar (dapat disesuaikan saat tuning):
```
urgency_score = (w1 * damage_severity) + (w2 * support_count_normalized)
              + (w3 * location_density_factor) + (w4 * category_urgency_weight)
```
- Bobot (`w1..w4`) dikonfigurasi di level sistem, bukan hard-coded di kode agar mudah di-tuning tanpa deploy ulang.
- Skor dihitung ulang setiap kali ada dukungan baru atau laporan baru di sekitar lokasi yang sama (radius dikonfigurasi, default 200m).

### 1.4 Aturan Dukungan (Support/Upvote)
- 1 user hanya bisa memberi 1 dukungan per laporan (enforced via unique constraint DB).
- Dukungan tidak dapat dibatalkan setelah diberikan (mencegah manipulasi skor berulang) — *kecuali* dalam 5 menit pertama (grace period untuk salah tap).

### 1.5 Aturan Citizen Validation
- Hanya pelapor asli **atau** warga dalam radius tertentu (mis. 100m dari lokasi) yang dapat melakukan validasi, untuk menjaga akurasi data lapangan.
- Jika dalam 7 hari sejak status `completed` tidak ada validasi warga → sistem otomatis set `resolved` (auto-resolve) agar laporan tidak menggantung selamanya.

### 1.6 Sistem Poin Kontribusi
| Aksi | Poin |
|---|---|
| Submit laporan valid (lolos verifikasi) | +10 |
| Laporan ditolak (rejected) | 0 (tidak ada penalti pertama kali) |
| Laporan ditolak berulang (indikasi spam, >3x dalam 30 hari) | -20 + flag akun untuk review admin |
| Memberi dukungan | +1 |
| Membatalkan dukungan (dalam grace period 5 menit) | -1 (menarik kembali poin yang diberikan) |
| Memberi citizen validation | +5 |

### 1.7 Routing Laporan ke Instansi
- Setiap `category` memiliki `default_agency_id` — laporan otomatis diarahkan (assigned_agency) ke instansi tersebut saat status `verified`.
- Operator dapat melakukan reassign manual jika kategori lintas instansi.

---

## 2. Validation Rules (Input)

### 2.1 Report Submission
| Field | Rule |
|---|---|
| photo | wajib, format JPEG/PNG, max 8MB, min resolusi 480p |
| latitude/longitude | wajib, harus berada dalam bounding box wilayah pilot (Kota Malang) untuk fase MVP |
| category | wajib, harus salah satu dari 5 kategori aktif (Jalan Berlubang, Lampu Jalan, Rambu, Trotoar, Drainase) |
| description | opsional saat submit (auto-filled AI), max 500 karakter jika diedit manual |

### 2.2 User Registration
| Field | Rule |
|---|---|
| email | wajib, format valid, unique |
| phone_number | wajib untuk OTP verification, format internasional valid, unique |
| password | min 8 karakter, kombinasi huruf & angka (jika pakai password-based auth) |
| role | default `citizen`; role lain hanya dapat diset oleh admin (tidak self-registration) |

### 2.3 Comment
- Max 300 karakter.
- Filter kata kasar/spam dasar (basic profanity filter): komentar disimpan apa adanya (tanpa masking) dan otomatis di-flag (`is_flagged=true`) untuk review moderator (SA-1).

---

## 3. API Design Rules (Backend)

- **Naming:** REST resource plural, kebab-case untuk path multi-kata (`/report-status-history`).
- **Versioning:** prefix `/api/v1/...` sejak awal untuk memudahkan perubahan breaking di masa depan.
- **Response envelope konsisten:**
```json
{
  "success": true,
  "data": { ... },
  "meta": { "page": 1, "total": 42 },
  "error": null
}
```
- **Error handling konsisten:**
```json
{
  "success": false,
  "data": null,
  "error": { "code": "REPORT_NOT_FOUND", "message": "Laporan tidak ditemukan" }
}
```
- **Status HTTP:** gunakan kode standar (`200`, `201`, `202` untuk proses async, `400` validasi, `401/403` auth, `404`, `409` konflik state, `500`).
- **Pagination:** cursor-based untuk list laporan (mendukung skala ribuan data), bukan offset-based.
- **Idempotency:** endpoint submit laporan menerima `idempotency_key` dari client untuk mencegah duplikasi akibat retry jaringan.

---

## 4. Coding Standards

### 4.1 Backend (NestJS/TypeScript)
- Struktur modular per domain (lihat Architecture doc), 1 modul = 1 folder (controller, service, dto, repository).
- DTO wajib pakai `class-validator` untuk validasi input di layer controller.
- Business logic **tidak boleh** ditulis di controller — controller hanya orkestrasi, logic di service.
- Semua akses DB melalui Prisma repository layer (tidak raw query kecuali kasus khusus dengan justifikasi).
- Penamaan: `camelCase` untuk variabel/fungsi, `PascalCase` untuk class/DTO, `snake_case` untuk kolom database.
- Wajib unit test untuk service yang mengandung business logic kritikal (Smart Priority, State Machine status).

### 4.2 Frontend (Flutter/Dart)
- Ikuti Clean Architecture layer (lihat Architecture doc) — widget tidak boleh langsung memanggil API/repository, harus lewat usecase/provider.
- Penamaan file: `snake_case.dart`; class: `PascalCase`; variabel/fungsi: `camelCase`.
- Semua warna & spacing **wajib** mengacu ke `core/theme` (design tokens), tidak hardcode hex value langsung di widget.
- Widget besar dipecah menjadi widget kecil reusable (`shared_widgets/`) — hindari 1 file widget >300 baris.
- State management: hindari `setState` untuk state kompleks/lintas layar — gunakan Riverpod/Bloc provider.
- Semua pemanggilan API dibungkus try-catch dengan mapping error ke pesan UI yang ramah pengguna (bukan raw exception).

### 4.3 Git & Workflow
- Branch: `main` (production), `develop` (staging), `feature/<nama-fitur>`, `fix/<nama-bug>`.
- Commit message: Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`).
- Pull request wajib direview minimal 1 anggota tim sebelum merge ke `develop`.

---

## 5. Data Governance & Privasi
- Foto laporan yang mengandung wajah/orang wajib melalui proses blur otomatis (opsional fase 2) sebelum tampil publik di peta.
- Data lokasi pelapor **tidak** ditampilkan sebagai identitas publik — hanya lokasi kerusakan yang publik, bukan lokasi rumah pelapor.
- Retensi data draft laporan lokal (belum terkirim) di device maksimal 7 hari sebelum otomatis dihapus.