# Design System — LaporKita

**Prinsip desain:** Clutter-free, data-storytelling, terkesan _sustainable_ & terpercaya (institusi pemerintah + teknologi).

---

## 1. Color Palette

Berdasarkan palet warna yang diberikan (_Selection colors_):

| Token                 | Hex       | Preview   | Penggunaan                                                                                  |
| --------------------- | --------- | --------- | ------------------------------------------------------------------------------------------- |
| `color/white`         | `#FFFFFF` | ⬜        | Background utama, permukaan card, teks di atas warna gelap                                  |
| `color/green-dark`    | `#206C57` | 🟩 (tua)  | Warna primer gelap — header, teks penting, ikon aktif, tombol primary-pressed               |
| `color/green-primary` | `#1D9C51` | 🟩        | Warna primer utama — tombol CTA, badge status positif/"selesai", progress bar, brand accent |
| `color/green-light`   | `#B9D19E` | 🟩 (muda) | Aksen sekunder — background badge ringan, highlight kartu, ilustrasi/heatmap zona "sedang"  |

### 1.1 Palet Turunan (untuk kebutuhan status & semantik)

Palet asli hanya hijau (brand color). Untuk status laporan (yang butuh diferensiasi merah/kuning/hijau sesuai mock-up "Menunggu Verifikasi / Sedang Diproses / Selesai" dan zona Urban Emotion Map), tambahkan warna semantik berikut agar tetap harmonis dengan palet hijau brand:

| Token                  | Hex (usulan)              | Penggunaan                                       |
| ---------------------- | ------------------------- | ------------------------------------------------ |
| `color/status-pending` | `#F5A623` (amber)         | Badge "Menunggu Verifikasi" / "Sedang Diproses"  |
| `color/status-danger`  | `#D64545` (merah)         | Badge "Ditolak" / zona stres tinggi / dispute    |
| `color/status-success` | `#1D9C51` (green-primary) | Badge "Selesai" / zona nyaman                    |
| `color/status-info`    | `#3B82C4` (biru)          | Info netral, link, marker peta kategori tertentu |
| `color/neutral-900`    | `#1A1A1A`                 | Teks utama                                       |
| `color/neutral-500`    | `#6B6B6B`                 | Teks sekunder / caption                          |
| `color/neutral-100`    | `#F2F4F3`                 | Background layar (bukan card)                    |
| `color/border`         | `#E2E8E4`                 | Divider, border card                             |

> Catatan: warna semantik di atas adalah usulan default tim desain dan **dapat disesuaikan** — namun brand hijau (`#206C57`, `#1D9C51`, `#B9D19E`) tetap menjadi identitas utama di semua layar.

### 1.2 Penerapan Warna per Komponen

| Komponen                        | Warna                                                                |
| ------------------------------- | -------------------------------------------------------------------- |
| Header/App bar                  | `green-primary` (#1D9C51) background, teks putih                     |
| Tombol Primary (CTA)            | Background `green-primary`, teks putih; pressed state → `green-dark` |
| Tombol Secondary/Outline        | Border `green-primary`, teks `green-primary`, background transparan  |
| Card                            | Background `white`, border `color/border`, shadow tipis              |
| Urban Health Score (radial)     | Ring progress `green-primary`, track `green-light`                   |
| Badge "Sedang Diproses"         | Background amber muda, teks amber tua                                |
| Badge "Selesai"                 | Background `green-light`, teks `green-dark`                          |
| Zona peta "nyaman/rendah stres" | `green-light` / `green-primary`                                      |
| Zona peta "stres tinggi"        | `status-danger`                                                      |
| Bottom navigation aktif         | Ikon & teks `green-primary`, non-aktif `neutral-500`                 |

---

## 2. Typography

| Style       | Font Size | Weight   | Penggunaan                              |
| ----------- | --------- | -------- | --------------------------------------- |
| Display     | 28px      | Bold     | Skor Urban Health Score, angka besar    |
| H1          | 22px      | Bold     | Judul layar                             |
| H2          | 18px      | SemiBold | Judul section (mis. "Laporan Terdekat") |
| Body        | 14px      | Regular  | Teks umum, deskripsi laporan            |
| Body Bold   | 14px      | SemiBold | Nama laporan pada card                  |
| Caption     | 12px      | Regular  | Metadata (tanggal, jumlah dukungan)     |
| Button Text | 14px      | SemiBold | Label tombol                            |

**Rekomendasi font family:** Inter / Plus Jakarta Sans (keterbacaan tinggi untuk data numerik, sesuai kebutuhan proposal "banyak menampilkan angka dan data").

---

## 3. Spacing & Layout

- Base unit: **4px** (skala: 4, 8, 12, 16, 24, 32)
- Padding standar card: 16px
- Jarak antar card dalam list: 12px
- Border radius: 12px (card), 8px (badge/chip), 999px (tombol pill/FAB kamera)
- Grid margin layar: 16px kiri-kanan

---

## 4. Komponen UI Utama

### 4.1 Report Card

```
┌─────────────────────────────────────┐
│ [Foto 64x64]  Jembatan Rusak         │
│               Jl. Toyiban No.13 f5   │
│               1.208 Dukungan  [Badge]│
└─────────────────────────────────────┘
```

- Background: white, radius 12px, shadow elevation-1
- Badge status pojok kanan: warna sesuai status (lihat 1.2)

### 4.2 Radial Progress (Urban Health Score / AI Confidence)

- Ring hijau (`green-primary`) di atas track (`green-light`)
- Angka besar di tengah (Display style)
- Label status di bawah angka (mis. "Sehat & Terkendali")

### 4.3 Status Timeline (Detail Laporan)

- Vertical stepper dengan titik (dot) terisi hijau untuk status terlewati, dot outline untuk status berjalan, dot abu untuk status belum tercapai
- Garis penghubung solid hijau untuk bagian yang sudah selesai, putus-putus/abu untuk bagian mendatang

### 4.4 Bottom Sheet (Peta)

- Radius atas 16px, drag handle di tengah atas
- Preview card laporan + tombol "Lihat Detail"

### 4.5 Kamera Overlay (Citizen Vision)

- Frame deteksi objek: border `green-primary`, label chip semi-transparan hitam dengan teks putih + persentase confidence
- Status chip (GPS Aktif, AI Ready, Internet Ok): pill kecil, background `green-dark` transparan 80%, teks putih, ikon check hijau muda

### 4.6 Tombol Shutter

- Lingkaran putih dengan border `green-primary` tebal (mengikuti mock-up kamera standar)

---

## 5. Ikonografi

- Gaya: outline/line-icon, konsisten stroke width 1.5–2px
- Warna default: `neutral-900` atau `green-primary` saat aktif
- Kategori fasilitas: ikon custom (jalan, trotoar, lampu, rambu, drainase) — line style agar konsisten dengan estetika "clutter-free"

---

## 6. Dark Mode (opsional, rekomendasi fase 2)

Karena warna dasar sudah cukup gelap (`#206C57`), dark mode dapat memakai:

- Background: `#121212`
- Card: `#1E1E1E`
- Primary tetap `#1D9C51` (kontras cukup di atas gelap)
- Teks: `#FFFFFF` / `#B9D19E` untuk aksen

---

## 7. Aksesibilitas

- Kontras teks putih di atas `green-primary` (#1D9C51): rasio ≈ 3.1:1 — cukup untuk teks besar/bold, **hindari** teks kecil regular di atas warna ini; gunakan `green-dark` (#206C57) untuk teks kecil agar rasio kontras lebih aman.
- Jangan hanya mengandalkan warna untuk status — selalu sertai label teks/ikon (mis. badge status selalu ada teks, bukan hanya warna dot).
