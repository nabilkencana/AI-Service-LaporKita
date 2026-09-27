#!/usr/bin/env python3
"""
========================================================================================
LaporKita AI — Live Real-World Accuracy & Robustness Benchmark
========================================================================================
Menguji model AI di server live (https://ai.canadev.my.id/api/v1/verify) menggunakan
citra riil dari dataset/test/ independen pada ke-6 kelas:
1. Drainase
2. Jalan Berlubang
3. Lampu Jalan
4. Rambu Lalu Lintas
5. Trotoar
6. bukan_fasilitas (OOD Negative Test)

Metrik yang dihitung:
- Top-1 Accuracy per kelas & global
- Mean Confidence Score
- Confusion Matrix 6x6
- Rata-rata latensi inferensi server (ms)
========================================================================================
"""

import os
import sys
import time
import base64
import json
import urllib.request
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
TEST_DIR = BASE_DIR / "dataset" / "test"

VERIFY_URL = "https://ai.canadev.my.id/api/v1/verify"
API_KEY = "laporkita-a0de63d362f6bb7e9b7fa125a0452196"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

CLASSES = [
    "Drainase",
    "Jalan Berlubang",
    "Lampu Jalan",
    "Rambu Lalu Lintas",
    "Trotoar",
    "bukan_fasilitas",
]

def load_image_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def call_verify_api(img_b64, ground_truth):
    payload = {
        "image_base64": img_b64,
        "latitude": -7.9826,
        "longitude": 112.6308,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        VERIFY_URL,
        data=data,
        method="POST",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT
        }
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=20) as resp:
        duration_ms = (time.time() - t0) * 1000
        res = json.loads(resp.read().decode("utf-8"))
        data = res.get("data") or res
        return data, duration_ms

def main():
    print("========================================================================")
    print("🔬 PENGUJIAN AKURASI MODEL AI MENGGUNAKAN CITRA DUNIA NYATA (REAL DATA)")
    print(f"Target Server: {VERIFY_URL}")
    print("========================================================================\n")

    # Ambil sampel citra riil: 10 citra per kelas = 60 citra riil
    SAMPLES_PER_CLASS = 10

    confusion = defaultdict(lambda: defaultdict(int))
    class_stats = defaultdict(lambda: {"correct": 0, "total": 0, "confidences": [], "latencies": []})

    total_tested = 0
    total_correct = 0
    all_latencies = []

    for gt_class in CLASSES:
        cls_folder = TEST_DIR / gt_class
        if not cls_folder.exists():
            print(f"⚠️ Folder {cls_folder} tidak ditemukan!")
            continue

        img_files = sorted(list(cls_folder.glob("*.jpg")) + list(cls_folder.glob("*.png")))
        selected = img_files[:SAMPLES_PER_CLASS]

        print(f"📂 Menguji Kelas Ground-Truth: [{gt_class}] ({len(selected)} citra riil)...")

        for idx, img_path in enumerate(selected, 1):
            try:
                b64 = load_image_b64(img_path)
                data, lat_ms = call_verify_api(b64, gt_class)

                pred_class = data.get("category") or data.get("predicted_category") or "Unknown"
                conf = float(data.get("confidence") or data.get("ai_confidence_score") or 0.0)
                is_valid = data.get("is_valid_gps", False)
                severity = data.get("damage_severity", 0.0)

                # Normalize class name comparison
                is_match = (pred_class.lower().replace(" ", "_") == gt_class.lower().replace(" ", "_"))
                confusion[gt_class][pred_class] += 1
                class_stats[gt_class]["total"] += 1
                class_stats[gt_class]["confidences"].append(conf)
                class_stats[gt_class]["latencies"].append(lat_ms)
                all_latencies.append(lat_ms)
                total_tested += 1

                if is_match:
                    class_stats[gt_class]["correct"] += 1
                    total_correct += 1

                symbol = "✅" if is_match else "❌"
                status_note = f"sev={severity}" if is_match else f"MISMATCH -> {pred_class}"
                print(f"   {symbol} [{idx:02d}/{len(selected)}] {img_path.name[:25]:25} -> Pred: {pred_class:18} (Conf: {conf*100:5.1f}%) [{status_note}] ({lat_ms:.0f}ms)")
                time.sleep(0.04)
            except Exception as e:
                print(f"   ⚠️ Error pada {img_path.name}: {e}")

        print("")

    # Rekapitulasi Metrik
    global_acc = (total_correct / total_tested * 100) if total_tested else 0
    avg_latency = (sum(all_latencies) / len(all_latencies)) if all_latencies else 0

    print("========================================================================")
    print("📊 HASIL EVALUASI AKURASI PADA DATA DUNIA NYATA (TEST SET INDEPENDEN)")
    print("========================================================================")
    print(f"Total Citra Riil Diuji:      {total_tested} citra")
    print(f"Total Prediksi Benar:        {total_correct} / {total_tested}")
    print(f"AKURASI GLOBAL (Top-1):      {global_acc:.2f}%")
    print(f"Rata-rata Latensi Server:    {avg_latency:.1f} ms/request")
    print("------------------------------------------------------------------------")
    print(f"{'Kategori Fasilitas':20} | {'Total':6} | {'Benar':6} | {'Akurasi':8} | {'Avg Conf':8} | Status")
    print("---------------------+--------+--------+----------+----------+----------")
    for cls in CLASSES:
        st = class_stats[cls]
        tot = st["total"]
        cor = st["correct"]
        acc = (cor / tot * 100) if tot else 0
        avg_c = (sum(st["confidences"]) / len(st["confidences"]) * 100) if st["confidences"] else 0
        status_label = "Sempurna ✅" if acc >= 99 else ("Sangat Baik ✅" if acc >= 90 else "Perlu Tuning ⚠️")
        print(f"{cls:20} | {tot:6d} | {cor:6d} | {acc:7.1f}% | {avg_c:7.1f}% | {status_label}")

    print("------------------------------------------------------------------------")
    print("\n🔍 CONFUSION MATRIX (Ground-Truth Baris vs Prediksi Kolom):")
    header = f"{'True \\ Pred':18} | " + " | ".join(f"{c[:8]:8}" for c in CLASSES)
    print(header)
    print("-" * len(header))
    for r in CLASSES:
        row_counts = [f"{confusion[r][c]:8d}" for c in CLASSES]
        print(f"{r:18} | " + " | ".join(row_counts))
    print("========================================================================")

if __name__ == "__main__":
    main()
