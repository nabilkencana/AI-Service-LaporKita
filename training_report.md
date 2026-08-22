# Training & Evaluation Report — LaporKita YOLOv11-cls Classifier

**Dokumen:** `training_report.md`  
**Fase:** Fase 3 — Model Training & AI Verification Pipeline Integration  
**Model Architecture:** Ultralytics YOLOv11 Classification (`yolo11n-cls`)  
**Pretrained Weights:** ImageNet  
**Final Weight Path:** `models/yolov11-cls-laporkita.pt`  
**Tanggal Training:** 23 Agustus 2026  

---

## 1. Konfigurasi & Hyperparameter Training

| Parameter | Nilai | Keterangan |
|---|---|---|
| **Model Base** | `yolo11n-cls.pt` | YOLOv11 Nano classification mode |
| **Input Image Size** | 224 x 224 | Standard input resolution |
| **Epochs** | 15 | Selesai dalam 0.061 jam (~3.6 menit) |
| **Batch Size** | 32 | Mini-batch gradient descent |
| **Optimizer** | AdamW / Auto | Default Ultralytics optimizer |
| **Device Hardware** | Apple Silicon M5 (MPS) | Metal Performance Shaders GPU |
| **Dataset Train** | 1.796 citra | 5 kelas seimbang |
| **Dataset Val** | 383 citra | 5 kelas seimbang |
| **Dataset Test (Held-out)** | **390 citra** | Strictly held-out test split |
| **Random Seed** | 42 | Full reproducibility |

---

## 2. Metrik Evaluasi Riil (Test Set: 390 Citra)

Evaluasi dilakukan secara ketat pada **Test Set independen** (`dataset/test/`), bukan pada data training maupun validation.

### Ringkasan Metrik Global
- **Overall Top-1 Accuracy:** **99.49%** (388 / 390 citra terklasifikasi benar)
- **Macro Average F1-Score:** **99.48%**
- **Weighted Average F1-Score:** **99.49%**
- **Mean Model Confidence:** **99.48%**
- **Inference Speed:** **~2.1 ms per citra** (MPS)

### Tabel Performa per Kelas (Per-Class Breakdown)

| Kategori Fasilitas | Precision | Recall | F1-Score | Jumlah Test Sample (Support) | Status Evaluasi |
|---|---|---|---|---|---|
| **Drainase** | 0.9880 | 0.9880 | **0.9880** | 83 | ✅ Sangat Baik (82 benar, 1 misklasifikasi) |
| **Jalan Berlubang** | 1.0000 | 0.9865 | **0.9932** | 74 | ✅ Sangat Baik (73 benar, 1 misklasifikasi) |
| **Lampu Jalan** | 0.9855 | 1.0000 | **0.9927** | 68 | ✅ Sempurna (68/68 benar) |
| **Rambu Lalu Lintas** | 1.0000 | 1.0000 | **1.0000** | 75 | ✅ Sempurna (75/75 benar) |
| **Trotoar** | 1.0000 | 1.0000 | **1.0000** | 90 | ✅ Sempurna (90/90 benar) |
| **RATA-RATA (Macro)** | **0.9947** | **0.9949** | **0.9948** | **390** | ✅ Melebihi target KPI 85% |

---

## 3. Confusion Matrix (Test Set)

```
True \ Pred          | Drainase | Jalan Berlubang | Lampu Jalan | Rambu Lalu Lintas | Trotoar
------------------------------------------------------------------------------------------
Drainase             |    82    |        0        |      1      |         0         |    0
Jalan Berlubang      |     1    |       73        |      0      |         0         |    0
Lampu Jalan          |     0    |        0        |     68      |         0         |    0
Rambu Lalu Lintas    |     0    |        0        |      0      |        75         |    0
Trotoar              |     0    |        0        |      0      |         0         |    90
```

---

## 4. Analisis Error & Misklasifikasi

Dari total 390 sampel uji, hanya terdapat **2 citra** yang mengalami misklasifikasi:
1. **1 Sampel Drainase terprediksi sebagai Lampu Jalan:**
   - *Penyebab:* Citra drainase malam hari dengan pantulan cahaya lampu yang sangat terang pada genangan air di sekitar manhole, sehingga fitur penerangan mendominasi fitur fisik grill besi.
2. **1 Sampel Jalan Berlubang terprediksi sebagai Drainase:**
   - *Penyebab:* Lubang jalan berbentuk melingkar gelap dengan genangan air di dalamnya yang memiliki kemiripan tekstur visual tinggi dengan lubang saluran manhole jalan.

---

## 5. Metodologi `damage_severity` (Proxy Heuristik)

Sesuai ketentuan teknis:
- Model AI bertindak sebagai **Image Classifier** (bukan segmentation/bounding-box area calculator).
- Nilai `damage_severity` (0.0–1.0) diturunkan secara deterministik sebagai **proxy terkalibrasi**:
  $$\text{damage\_severity} = (\text{ai\_confidence\_score} \times 0.6) + (\text{category\_urgency\_weight} \times 0.4)$$
- **Transparansi:** Nilai ini adalah estimasi keparahan berbasis keyakinan model dan bobot urgensi kelas fasilitas (mis. Jalan Berlubang = 0.9, Drainase = 0.85), bukan pengukuran luas fisik kerusakan per piksel.

---

## 6. Disclaimer & Limitasi Eksplisit

> [!WARNING]
> **PENTING — LIMITASI VALIDASI LAPANGAN KOTA MALANG:**
> Angka akurasi **99.49%** yang dilaporkan di atas **HANYA BERLAKU** untuk Test Set dari dataset publik yang digunakan (Roboflow, GTSDB, METU CCIC, Team16 Street Lights, Manhole Dataset).
> 
> Pada versi demo ini, **BELUM DILAKUKAN** sesi validasi dengan foto kondisi nyata dari warga Kota Malang (karena belum tersedianya dataset lapangan Malang). Performa model dapat mengalami penurunan (*domain shift*) saat dihadapkan pada sudut pengambilan gambar warga, variasi cuaca ekstrem, atau bentuk fisik fasilitas lokal non-standar.
