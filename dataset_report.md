# Dataset Acquisition & Unification Report — LaporKita AI Service

**Dokumen:** `dataset_report.md`  
**Fase:** Fase 2 — Data Acquisition, Cleaning, Unifikasi Label & Stratified Split  
**Target Model:** Image Classification (5 Kelas) untuk Ultralytics Classification Mode (`yolo11-cls`)  
**Tanggal:** 23 Agustus 2026  

---

## 1. Sumber Dataset Publik & Lisensi

Seluruh data yang digunakan dalam pipeline ini berasal dari dataset publik terbuka dengan lisensi riset/komersial yang terverifikasi.

| Kategori LaporKita | Nama Dataset Publik | Sumber Persis / URL Verifikasi | Lisensi | Raw Download |
|---|---|---|---|---|
| **Jalan Berlubang** | Roboflow Pothole Dataset & Andyrasika Potholes Dataset (CRDDC RDD2022 subset) | [HuggingFace: keremberke/pothole-segmentation](https://huggingface.co/datasets/keremberke/pothole-segmentation)<br>[HuggingFace: Andyrasika/potholes-dataset](https://huggingface.co/datasets/Andyrasika/potholes-dataset)<br>[Figshare: RDD2022 (doi: 10.6084/m9.figshare.21431547)](https://doi.org/10.6084/m9.figshare.21431547) | CC BY 4.0 / MIT | 490 |
| **Trotoar** | METU Concrete Crack Images for Classification (CCIC, Çağlar Fırat Özgenel, 2019) | [Mendeley Data: 5y9wdsg2zt/2 (doi: 10.17632/5y9wdsg2zt.2)](https://data.mendeley.com/datasets/5y9wdsg2zt/2)<br>[HuggingFace: mohammadnajeeb/concrete_crack_images](https://huggingface.co/datasets/mohammadnajeeb/concrete_crack_images) | CC BY 4.0 | 600 |
| **Rambu Lalu Lintas** | German Traffic Sign Detection Benchmark (GTSDB / Roboflow traffic signs) | [HuggingFace: keremberke/german-traffic-sign-detection](https://huggingface.co/datasets/keremberke/german-traffic-sign-detection) | CC BY 4.0 | 491 |
| **Lampu Jalan** | Team16 Street Light Dataset & Roboflow Damaged Lights | [GitHub: Team16Project/Street-Light-Dataset](https://github.com/Team16Project/Street-Light-Dataset)<br>[Roboflow Universe: godspeed-yqpeo/damaged-lights](https://universe.roboflow.com/godspeed-yqpeo/damaged-lights) | MIT / CC BY 4.0 | 450 |
| **Drainase** | Manhole Covers Dataset & Roboflow Storm Drains | [HuggingFace: delima87/manhole_covers_dataset](https://huggingface.co/datasets/delima87/manhole_covers_dataset)<br>[Roboflow Universe: new-workspace-zyqyt/storm-drain-model](https://universe.roboflow.com/new-workspace-zyqyt/storm-drain-model) | CC BY 4.0 | 550 |

---

## 2. Tabel Pemetaan Label (Label Unification Mapping)

Keputusan penyederhanaan dan penggabungan sub-label dari dataset asli ke 5 kelas standar LaporKita:

| Label Asli (Source Dataset) | Label Final LaporKita | Rasional & Keputusan Penyederhanaan |
|---|---|---|
| `pothole`, `pothole-and-crack`, `D40` (Pothole), `D00` (Longitudinal Crack), `D10` (Transverse Crack), `D20` (Alligator Crack) | **`Jalan Berlubang`** | Seluruh jenis defek permukaan aspal (lubang dan retak struktural) dikelompokkan ke satu kategori pelaporan jalan untuk konsistensi routing dinas DPUPR. |
| `Positive` (Surface Crack on Concrete Slabs / Sidewalks) | **`Trotoar`** | Menggunakan citra retak dan degradasi permukaan beton sebagai representasi kondisi trotoar/jalur pedestrian yang rusak. |
| `traffic_sign`, `prohibitory`, `danger`, `mandatory`, `damaged_sign` | **`Rambu Lalu Lintas`** | Semua jenis rambu (peringatan, larangan, petunjuk, maupun kerusakan fisik rambu) disatukan ke dalam kategori rambu lalu lintas untuk Dishub. |
| `Not Working`, `Working`, `Broken Streetlight`, `street_light` | **`Lampu Jalan`** | Objek penerangan jalan umum (PJU) baik kondisi mati, rusak fisik, maupun tiang lampu jalan disatukan ke kategori PJU. |
| `manhole_cover`, `storm_drain`, `drain`, `drainage` | **`Drainase`** | Saluran air hujan (storm drain), grill besi resapan, dan penutup saluran drainase jalan disatukan ke kategori drainase untuk DPUPR. |

---

## 3. Proses Data Cleaning & Validasi

Proses pembersihan dilakukan secara otomatis menggunakan skrip [`scripts/prepare_dataset.py`](file:///Users/nabilkencana/Project%20/Lomba%20MAGEITS/ai-service/scripts/prepare_dataset.py):
1. **Validasi Format & Integritas File:** Setiap file diverifikasi dengan `PIL.Image.open().verify()` untuk memastikan tidak ada file gambar yang korup atau terpotong.
2. **Standardisasi Warna:** Seluruh gambar dikonversi ke mode `RGB` (menghapus alpha channel RGBA / grayscale 1-channel).
3. **Filter Resolusi Minimal:** Gambar dengan dimensi di bawah 32x32 piksel secara otomatis dibuang.
4. **Deduplikasi (MD5 Hash Matching):** Gambar duplikat diidentifikasi melalui checksum konten hash MD5 dan dieliminasi sebelum proses splitting.

---

## 4. Distribusi Sample Final per Split (70/15/15)

Data dibagi menggunakan teknik **Stratified Split** dengan rasio:
- **Train Set:** 70%
- **Validation Set:** 15%
- **Test Set:** 15%
- **Random Seed:** 42 (reproducible)

| Kategori LaporKita | Raw Download | Corrupted Removed | Duplicates Removed | Total Clean & Unique | Train (70%) | Val (15%) | Test (15%) |
|---|---|---|---|---|---|---|---|
| **Jalan Berlubang** | 490 | 0 | 4 | **486** | 340 | 72 | 74 |
| **Trotoar** | 600 | 0 | 0 | **600** | 420 | 90 | 90 |
| **Rambu Lalu Lintas** | 491 | 0 | 0 | **491** | 343 | 73 | 75 |
| **Lampu Jalan** | 450 | 0 | 3 | **447** | 312 | 67 | 68 |
| **Drainase** | 550 | 0 | 5 | **545** | 381 | 81 | 83 |
| **TOTAL** | **2.581** | **0** | **12** | **2.569** | **1.796** | **383** | **390** |

---

## 5. Struktur Folder Dataset Siap Training

Dataset telah disimpan dalam format standar klasifikasi Ultralytics (`dataset/<split>/<class_name>/`):

```
dataset/
├── train/
│   ├── Drainase/             (381 files)
│   ├── Jalan Berlubang/      (340 files)
│   ├── Lampu Jalan/          (312 files)
│   ├── Rambu Lalu Lintas/    (343 files)
│   └── Trotoar/              (420 files)
├── val/
│   ├── Drainase/             (81 files)
│   ├── Jalan Berlubang/      (72 files)
│   ├── Lampu Jalan/          (67 files)
│   ├── Rambu Lalu Lintas/    (73 files)
│   └── Trotoar/              (90 files)
└── test/
    ├── Drainase/             (83 files)
    ├── Jalan Berlubang/      (74 files)
    ├── Lampu Jalan/          (68 files)
    ├── Rambu Lalu Lintas/    (75 files)
    └── Trotoar/              (90 files)
```

---

## 6. Catatan Risiko & Limitasi per Kategori

Sesuai **Keputusan Final #2 & #3**, metrik akurasi yang akan dihasilkan pada Fase 3 **hanya mencerminkan evaluasi pada test set dataset publik di atas**, bukan jaminan performa di foto lapangan warga Kota Malang.

Berikut analisis risiko domain shift spesifik per kategori:

1. **Jalan Berlubang (Road Damage):**
   - *Karakteristik Data:* Menggunakan citra aspal jalan dari subset CRDDC RDD2022 (Jepang, India, dsb.).
   - *Risiko Domain:* Variasi marka jalan dan tekstur aspal di Malang (mis. tambalan aspal manual, jalan berpasir) dapat menyebabkan perbedaan distribusi visual.

2. **Trotoar (Sidewalk Concrete):**
   - *Karakteristik Data:* Citra berasal dari dataset keretakan pelat beton universitas (METU CCIC).
   - *Risiko Domain:* Citra berupa close-up keretakan beton, bukan pemandangan trotoar perkotaan Indonesia lengkap dengan paving block atau pohon peneduh.

3. **Rambu Lalu Lintas (Traffic Signs):**
   - *Karakteristik Data:* Menggunakan rambu lalu lintas internasional/Eropa (GTSDB).
   - *Risiko Domain:* Piktogram, bentuk rambu, dan bahasa pada rambu lokal Dishub Kota Malang mungkin berbeda dari dataset standar Jerman/Eropa.

4. **Lampu Jalan (Street Lights):**
   - *Karakteristik Data:* Berisi tiang dan lampu jalan siang/malam (Team16 Street Light Dataset).
   - *Risiko Domain:* Desain ornamen tiang PJU Kota Malang (tiang antik heritage atau tiang konvensional) memiliki variasi bentuk fisik yang khas.

5. **Drainase (Storm Drains):**
   - *Karakteristik Data:* Berisi grill besi penutup saluran air jalan dan manhole cover perkotaan modern.
   - *Risiko Domain:* Banyak saluran drainase di lingkungan perumahan/kampung Malang berbentuk selokan terbuka (parit terbuka) tanpa penutup besi, yang belum terwakili secara penuh pada dataset manhole publik.
