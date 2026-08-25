#!/usr/bin/env python3
"""
========================================================================================
Automated YOLOv11 Retraining & Continuous Fine-Tuning Pipeline
========================================================================================
Runs transfer learning on YOLOv11-cls using human-verified active learning datasets.
========================================================================================
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SPLIT_DIR = BASE_DIR / "data" / "active_learning" / "split"
BASE_MODEL = BASE_DIR / "app" / "models" / "yolov11_classification.pt"
OUTPUT_MODEL_DIR = BASE_DIR / "app" / "models" / "active_learning_runs"


def run_retraining(epochs: int = 30, batch_size: int = 16, img_size: int = 224):
    print("====================================================================")
    print("🚀 LaporKita AI - Continuous Active Learning Retraining Pipeline")
    print("====================================================================")

    if not SPLIT_DIR.exists() or not (SPLIT_DIR / "train").exists():
        print("❌ Dataset split tidak ditemukan. Menjalankan export dataset...")
        try:
            from scripts.export_active_dataset import export_dataset
        except ImportError:
            # pyrefly: ignore [missing-import]
            from export_active_dataset import export_dataset
        export_dataset()

    try:
        from ultralytics import YOLO
    except ImportError:
        print("❌ Ultralytics tidak terpasang. Jalankan: pip install ultralytics")
        sys.exit(1)

    weights_to_load = str(BASE_MODEL) if BASE_MODEL.exists() else "yolo11n-cls.pt"
    print(f"📦 Loading base model weights: {weights_to_load}")
    model = YOLO(weights_to_load)

    OUTPUT_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print(f"🏋️ Memulai fine-tuning transfer learning ({epochs} epochs, batch={batch_size})...")
    results = model.train(
        data=str(SPLIT_DIR),
        epochs=epochs,
        imgsz=img_size,
        batch=batch_size,
        project=str(OUTPUT_MODEL_DIR),
        name="run_latest",
        exist_ok=True,
        verbose=True,
    )

    print("\n✅ Fine-tuning selesai!")
    print(f"📊 Model artifact baru tersimpan di: {OUTPUT_MODEL_DIR / 'run_latest' / 'weights' / 'best.pt'}")


if __name__ == "__main__":
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    run_retraining(epochs=epochs)
