"""
Download real-world negative samples (picsum photos) untuk kelas 'bukan_fasilitas'.
Menghasilkan ~210 foto asli beragam (lanskap, objek, arsitektur, dll) untuk
memperkuat batas OOD model (FIX ROUND 3).

Usage:
    python scripts/download_real_negatives.py [count] [output_dir]

Output default: dataset_staging/bukan_fasilitas_real/
Setelah diunduh, distribusikan ke dataset/{train,val,test}/bukan_fasilitas/
lalu jalankan scripts/rebuild_clean_dataset.py + scripts/train_yolo_classifier.py.
"""

import os
import random
import sys
import time
import urllib.request
from pathlib import Path


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 210
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(
        __file__).resolve().parent.parent / "dataset_staging" / "bukan_fasilitas_real"
    out_dir.mkdir(parents=True, exist_ok=True)

    random.seed(2026)
    seeds = random.sample(range(1, 100000), count)

    ok = 0
    for i, s in enumerate(seeds):
        url = f"https://picsum.photos/seed/{s}/640/480"
        dest = out_dir / f"real_neg_{s}.jpg"
        if dest.exists():
            ok += 1
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=25) as r, open(dest, "wb") as f:
                f.write(r.read())
            ok += 1
        except Exception as e:
            print(f"  gagal seed {s}: {e}")
        if i % 50 == 49:
            print(f"  progress {i + 1}/{count} (ok={ok})")
        time.sleep(0.05)

    print(f"TOTAL foto asli terunduh: {ok} -> {out_dir}")


if __name__ == "__main__":
    main()
