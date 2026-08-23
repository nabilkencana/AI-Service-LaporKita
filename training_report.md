# Training & Evaluation Report — LaporKita YOLOv11-cls 6-Class Classifier

**Dokumen:** `training_report.md`  
**Fase:** FIX ROUND 2 — 6-Class Implementation (`bukan_fasilitas` OOD Guard)  
**Model Architecture:** Ultralytics YOLOv11 Classification (`yolo11n-cls`)  
**Pretrained Weights:** ImageNet  
**Final Weight Path:** `models/yolov11-cls-laporkita.pt` (3.2 MB)  
**Tanggal Training:** 23 Agustus 2026  

---

## 1. Konfigurasi & Hyperparameter Training

| Parameter | Nilai | Keterangan |
|---|---|---|
| **Model Base** | `yolo11n-cls.pt` | YOLOv11 Nano classification mode |
| **Input Image Size** | 224 x 224 | Standard input resolution |
| **Epochs** | 20 | Selesai dalam ~5.9 menit (0.099 hours) |
| **Batch Size** | 32 | Mini-batch gradient descent |
| **Augmentation** | `degrees=180.0, fliplr=0.5, flipud=0.5` | Augmentasi rotasi & flip penuh (solusi MODEL-ROT) |
| **Optimizer** | AdamW / Auto | Default Ultralytics optimizer |
| **Device Hardware** | Apple Silicon (MPS / Apple M5) | Metal Performance Shaders GPU |
| **Dataset Train** | **2.040 citra** | 6 kelas seimbang |
| **Dataset Val** | **422 citra** | 6 kelas seimbang |
| **Dataset Test (Held-out)** | **457 citra** | **Leak-Free Verified Test Split** (dHash distance > 8 antar train & test) |
| **Random Seed** | 42 | Full reproducibility |

---

## 2. Metrik Evaluasi Riil (Test Set Bebas Kebocoran: 457 Citra)

Evaluasi dilakukan pada **Held-out Test Set 6-Kelas independen bebas kebocoran** (`dataset/test/`), setelah dilakukan pengelompokan perceptual hash (`dHash`) dan sekuens video sumber (**Fix LEAK-1**).

### Ringkasan Metrik Global
- **Overall Top-1 Accuracy:** **99.56%** (455 / 457 citra terklasifikasi benar)
- **Overall 95% Confidence Interval (Wilson Score):** **98.42% – 99.88%**
- **Macro Average F1-Score:** **99.56%**
- **Weighted Average F1-Score:** **99.56%**
- **Mean Model Confidence:** **99.36%**
- **Inference Speed:** **0.4 ms inference per image** (MPS)

### Tabel Performa per Kelas (6 Kelas Lengkap + Wilson 95% CI)

| Kategori Fasilitas | Precision | Recall | F1-Score | Support | 95% CI Recall (Wilson) | Status Evaluasi |
|---|---|---|---|---|---|---|
| **Drainase** | 1.0000 | 1.0000 | **1.0000** | 83 | 95.58% – 100.00% | ✅ Sempurna (83/83 benar) |
| **Jalan Berlubang** | 0.9737 | 1.0000 | **0.9867** | 74 | 95.07% – 100.00% | ✅ Sempurna (74/74 benar) |
| **Lampu Jalan** | 1.0000 | 0.9877 | **0.9938** | 81 | 93.33% – 99.78% | ✅ Sangat Baik (80/81 benar, 1 ke JB) |
| **Rambu Lalu Lintas** | 1.0000 | 0.9867 | **0.9933** | 75 | 92.83% – 99.76% | ✅ Sangat Baik (74/75 benar, 1 ke JB) |
| **Trotoar** | 1.0000 | 1.0000 | **1.0000** | 90 | 95.91% – 100.00% | ✅ Sempurna (90/90 benar) |
| **bukan_fasilitas (OOD)** | 1.0000 | 1.0000 | **1.0000** | 54 | 93.36% – 100.00% | ✅ Sempurna (54/54 benar OOD) |
| **RATA-RATA (Macro)** | **0.9956** | **0.9957** | **0.9956** | **457** | **98.42% – 99.88%** | ✅ Melebihi target KPI 85% |

---

## 3. Confusion Matrix 6×6 (Test Set Aktual)

```
True \ Pred          | Drainase | Jalan Berlubang | Lampu Jalan | Rambu Lalu Lintas | Trotoar | bukan_fasilitas
-------------------------------------------------------------------------------------------------------------
Drainase             |    83    |        0        |      0      |         0         |    0    |        0
Jalan Berlubang      |     0    |       74        |      0      |         0         |    0    |        0
Lampu Jalan          |     0    |        1        |     80      |         0         |    0    |        0
Rambu Lalu Lintas    |     0    |        1        |      0      |        74         |    0    |        0
Trotoar              |     0    |        0        |      0      |         0         |   90    |        0
bukan_fasilitas      |     0    |        0        |      0      |         0         |    0    |       54
```

---

## 4. Evaluasi OOD & Sampel Negatif (Acceptance FIX-1)

Model diuji terhadap sampel non-fasilitas yang sebelumnya gagal pada Round 1:
1. **Abu-abu polos (4000×3000):** Terprediksi `bukan_fasilitas` (Confidence 99.99%) $\to$ `is_valid=false`, `needs_manual_review=true`.
2. **Gradient multi-warna:** Terprediksi `bukan_fasilitas` (Confidence 99.99%) $\to$ `is_valid=false`, `needs_manual_review=true`.
3. **Noise acak (Gaussian / Uniform):** Terprediksi `bukan_fasilitas` (Confidence 99.99%) $\to$ `is_valid=false`, `needs_manual_review=true`.
4. **Foto acak (dokumen, teks, pemandangan luar jalan):** Terprediksi `bukan_fasilitas` (Confidence 99.99%).

---

## 5. Distribusi Resolusi Citra & Kalibrasi RES-480

Analisis empiris terhadap 457 sampel test set:
- **Rentang Resolusi Sisi Terpanjang:** 200px – 1360px (Median: 227px).
- Sebanyak **60.4% (276 citra)** memiliki resolusi antara 200px dan 479px (karena standar crop dataset publik benchmark seperti RDD2020 / METU CCIC).
- **Keputusan Kalibrasi Server:** `MIN_IMAGE_DIMENSION` disetel ke **200px** untuk mengizinkan gambar benchmark valid dan crop kamera mobile tanpa menolak pipeline secara keliru, namun tetap menolak gambar thumbnail berukuran mikro / rusak (< 200px) dengan pesan error HTTP 422 yang jelas.
- **Deteksi Blur (DEG-ROBUST):** Laplacian variance threshold dikalibrasi ke **`1.5`** (citra blur berat memiliki variance 1.08–1.56, sementara citra normal memiliki median variance 371.15).

---

## 6. Disclaimer & Limitasi Eksplisit

> [!WARNING]
> **PENTING — LIMITASI VALIDASI LAPANGAN KOTA MALANG:**
> Angka akurasi **99.56%** yang dilaporkan di atas **HANYA BERLAKU** untuk Test Set bersih dari dataset publik yang digunakan (Roboflow, GTSDB, METU CCIC, Team16 Street Lights, Manhole Dataset, dan Sintetis OOD).
> 
> Pada versi demo ini, **BELUM DILAKUKAN** validasi dengan foto kondisi nyata dari warga Kota Malang (karena belum tersedianya dataset lapangan Malang). Performa model dapat mengalami penurunan (*domain shift*) saat dihadapkan pada sudut pengambilan gambar warga, variasi cuaca ekstrem, atau bentuk fisik fasilitas lokal non-standar.
