# Training & Evaluation Report — LaporKita YOLOv11-cls 6-Class Classifier

**Dokumen:** `training_report.md`  
**Fase:** FIX ROUND 3 — 6-Class dengan Sampel Negatif Dunia Nyata (`bukan_fasilitas` OOD Guard)  
**Model Architecture:** Ultralytics YOLOv11 Classification (`yolo11n-cls`)  
**Pretrained Weights:** ImageNet  
**Final Weight Path:** `models/yolov11-cls-laporkita.pt` (3.2 MB)  
**Tanggal Training:** 23 Agustus 2026 (retrain kedua, +210 foto asli negatif)

---

## 1. Konfigurasi & Hyperparameter Training

| Parameter | Nilai | Keterangan |
|---|---|---|
| **Model Base** | `yolo11n-cls.pt` | YOLOv11 Nano classification mode |
| **Input Image Size** | 224 x 224 | Standard input resolution |
| **Epochs** | 20 | Selesai ±7 menit |
| **Batch Size** | 32 | Mini-batch gradient descent |
| **Augmentation** | `degrees=180.0, fliplr=0.5, flipud=0.5` | Augmentasi rotasi & flip penuh (solusi MODEL-ROT) |
| **Optimizer** | AdamW / Auto | Default Ultralytics optimizer |
| **Device Hardware** | Apple Silicon (MPS) | Metal Performance Shaders GPU |
| **Dataset Train** | **2.188 citra** | 6 kelas (bukan_fasilitas: 392) |
| **Dataset Val** | **433 citra** | 6 kelas (bukan_fasilitas: 63) |
| **Dataset Test (Held-out)** | **508 citra** | **Leak-Free Verified** (dHash ≤ 4: 0 pasang train↔test) |
| **Sampel Negatif** | 560 total | 350 sintetis + **210 foto asli dunia nyata** (picsum: lanskap, objek, orang, dll) |
| **Random Seed** | 42 | Full reproducibility |

---

## 2. Metrik Evaluasi Riil (Test Set Bebas Kebocoran: 508 Citra)

Evaluasi dilakukan pada **Held-out Test Set 6-Kelas independen bebas kebocoran** (`dataset/test/`), setelah pengelompokan perceptual hash (`dHash`) dan sekuens video sumber (**Fix LEAK-1**).

### Ringkasan Metrik Global
- **Overall Top-1 Accuracy:** **99.02%** (503 / 508 citra terklasifikasi benar)
- **Overall 95% Confidence Interval (Wilson Score):** **97.72% – 99.58%**
- **Macro Average F1-Score:** **99.04%**
- **Mean Model Confidence:** 99%+ (kelas asli ≥ 0.99 pada verifikasi live)

### Tabel Performa per Kelas (6 Kelas Lengkap + Wilson 95% CI)

| Kategori Fasilitas | Precision | Recall | F1-Score | Support | 95% CI Recall (Wilson) | Status Evaluasi |
|---|---|---|---|---|---|---|
| **Drainase** | 0.9881 | 1.0000 | **0.9940** | 83 | 95.58% – 100.00% | ✅ Sempurna (83/83 benar) |
| **Jalan Berlubang** | 1.0000 | 0.9865 | **0.9932** | 74 | 92.73% – 99.76% | ✅ Sangat Baik (73/74 benar, 1 ke Rambu) |
| **Lampu Jalan** | 1.0000 | 0.9877 | **0.9938** | 81 | 93.33% – 99.78% | ✅ Sangat Baik (80/81 benar, 1 ke bukan_fasilitas) |
| **Rambu Lalu Lintas** | 0.9615 | 1.0000 | **0.9804** | 75 | 95.13% – 100.00% | ✅ Sempurna (75/75 benar) |
| **Trotoar** | 1.0000 | 1.0000 | **1.0000** | 90 | 95.91% – 100.00% | ✅ Sempurna (90/90 benar) |
| **bukan_fasilitas (OOD)** | 0.9903 | 0.9714 | **0.9808** | 105 | 91.93% – 99.02% | ✅ Sangat Baik (102/105 benar; 1 ke Drainase, 2 ke Rambu) |
| **RATA-RATA (Macro)** | **0.9901** | **0.9909** | **0.9904** | **508** | **97.72% – 99.58%** | ✅ Melebihi target KPI 85% |

---

## 3. Confusion Matrix 6×6 (Test Set Aktual)

```
True \ Pred          | Drainase | Jalan Berlubang | Lampu Jalan | Rambu Lalu Lintas | Trotoar | bukan_fasilitas
-------------------------------------------------------------------------------------------------------------
Drainase             |    83    |       0         |      0      |         0         |    0    |       0
Jalan Berlubang      |     0    |      73         |      0      |         1         |    0    |       0
Lampu Jalan          |     0    |       0         |     80      |         0         |    0    |       1
Rambu Lalu Lintas    |     0    |       0         |      0      |        75         |    0    |       0
Trotoar              |     0    |       0         |      0      |         0         |   90    |       0
bukan_fasilitas      |     1    |       0         |      0      |         2         |    0    |     102
```

---

## 4. Verifikasi Live Pasca-Retrain (foto asing yang sebelumnya bocor)

Foto asing acak (picsum) yang pada model Round 2 bocor ke 5 kelas asli dengan
confidence tinggi (0.90–0.99, auto-verified) — setelah retrain dengan sampel
negatif dunia nyata, SEMUA kini terprediksi `bukan_fasilitas`:

| Input | Round 2 (sebelum) | Round 3 (sesudah) |
|---|---|---|
| picsum-42 | Rambu 0.73 → auto | **bukan_fasilitas** 1.00 → invalid |
| picsum-100 | Rambu 0.90 → auto | **bukan_fasilitas** 1.00 → invalid |
| picsum-101 | Jalan Berlubang 0.99 → auto | **bukan_fasilitas** 0.95 → invalid |
| picsum-102 | Lampu Jalan 0.74 → auto | **bukan_fasilitas** 0.73 → invalid |
| picsum-104 | Drainase 0.52 | **bukan_fasilitas** 0.99 → invalid |
| Abu-abu 4000×3000 | Drainase 0.997 → auto | **bukan_fasilitas** 1.00 → invalid |
| Noise | — | **bukan_fasilitas** → invalid |

Kelas asli tidak regresi: sampel test Rambu/Jalan Berlubang/Trotoar tetap
terprediksi benar dengan confidence 1.00 dan `is_valid=true`.

---

## 5. Catatan

- Retrain ini menutup celah OOD foto asing ber-confidence tinggi (temuan
  Re-QA Round 3). Batas tersisa (foto yang visualnya nyaris identik dengan
  kelas asli) tetap dimitigasi aturan dua-ambang confidence (0.6/0.85).
- Dataset negatif (gitignored) dapat diregenerasi via
  `scripts/generate_negative_samples.py` + `scripts/download_real_negatives.py`.
