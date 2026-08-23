"""
Training & Evaluation Pipeline for LaporKita 5-Class Facility Damage Classifier.
Uses Ultralytics YOLOv11 classification mode (yolo11n-cls).
Evaluates strictly on the held-out TEST SET and computes true metrics.
"""

import os
import json
import shutil
from pathlib import Path
import numpy as np
from PIL import Image
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from ultralytics import YOLO
import torch

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "dataset"
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

FINAL_WEIGHT_PATH = MODELS_DIR / "yolov11-cls-laporkita.pt"
METRICS_JSON_PATH = MODELS_DIR / "classification_metrics.json"

CLASSES = [
    "Drainase",
    "Jalan Berlubang",
    "Lampu Jalan",
    "Rambu Lalu Lintas",
    "Trotoar",
    "bukan_fasilitas",
]


def wilson_score_interval(k: int, n: int, confidence: float = 0.95) -> dict:
    """Calculates Wilson score 95% confidence interval for a proportion."""
    if n == 0:
        return {"low": 0.0, "high": 0.0, "ci_str": "0.00% - 0.00%"}
    z = 1.95996  # 95% confidence
    p = k / n
    denom = 1 + (z**2) / n
    center = (p + (z**2) / (2 * n)) / denom
    spread = (z * np.sqrt((p * (1 - p) + (z**2) / (4 * n)) / n)) / denom
    low = max(0.0, float(center - spread))
    high = min(1.0, float(center + spread))
    return {
        "low": round(low, 4),
        "high": round(high, 4),
        "ci_str": f"{low * 100:.2f}% - {high * 100:.2f}%",
    }


def train_classifier():
    print("=" * 60)
    print("LAPORKITA YOLOv11-CLS MODEL TRAINING")
    print("=" * 60)

    # Check device: MPS (Apple Silicon), CUDA, or CPU
    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = 0
    else:
        device = "cpu"
    print(f"Using compute device: {device}")

    # Initialize YOLOv11-cls pretrained model
    model = YOLO("yolo11n-cls.pt")

    # Train model with data augmentation (including rotation & flip for MODEL-ROT fix)
    print(f"Starting training on {DATASET_DIR.resolve()}...")
    results = model.train(
        data=str(DATASET_DIR.resolve()),
        epochs=20,
        imgsz=224,
        batch=32,
        degrees=180.0,
        fliplr=0.5,
        flipud=0.5,
        device=device,
        project=str(BASE_DIR / "runs" / "classify"),
        name="laporkita_yolo11_cls",
        exist_ok=True,
        workers=4,
        verbose=True,
        seed=42,
    )

    # Find and copy best weights
    best_weight = Path(results.save_dir) / "weights" / "best.pt"
    if best_weight.exists():
        shutil.copy(best_weight, FINAL_WEIGHT_PATH)
        print(f"Successfully copied best weight to: {FINAL_WEIGHT_PATH}")
    else:
        print(f"Warning: {best_weight} not found, saving active model")
        model.save(str(FINAL_WEIGHT_PATH))

    return FINAL_WEIGHT_PATH


def evaluate_on_test_set(weight_path: Path):
    print("\n" + "=" * 60)
    print("EVALUATING MODEL ON HELD-OUT TEST SET (390 SAMPLES)")
    print("=" * 60)

    model = YOLO(str(weight_path))
    test_dir = DATASET_DIR / "test"

    y_true = []
    y_pred = []
    confidences = []
    filenames = []

    # Map model class names to indices
    model_names = model.names
    print(f"Model class mapping: {model_names}")

    test_classes = sorted([d.name for d in test_dir.iterdir() if d.is_dir()])

    for true_cls in test_classes:
        cls_folder = test_dir / true_cls
        img_files = list(cls_folder.glob("*.jpg")) + list(cls_folder.glob("*.png"))
        print(f"Evaluating class '{true_cls}': {len(img_files)} images...")

        for img_path in img_files:
            try:
                res = model.predict(source=str(img_path), verbose=False)[0]
                top1_idx = res.probs.top1
                top1_conf = float(res.probs.top1conf.cpu().item())
                pred_cls = model_names[top1_idx]

                y_true.append(true_cls)
                y_pred.append(pred_cls)
                confidences.append(top1_conf)
                filenames.append(img_path.name)
            except Exception as e:
                print(f"Error predicting {img_path}: {e}")

    # Compute Metrics
    overall_acc = accuracy_score(y_true, y_pred)
    cls_report = classification_report(y_true, y_pred, target_names=CLASSES, output_dict=True, zero_division=0)
    conf_mat = confusion_matrix(y_true, y_pred, labels=CLASSES)

    print("\n" + "=" * 60)
    print(f"TEST SET EVALUATION RESULTS (REAL TEST ACCURACY: {overall_acc * 100:.2f}%)")
    print("=" * 60)
    print(classification_report(y_true, y_pred, target_names=CLASSES, zero_division=0))
    print("Confusion Matrix:")
    header_label = "True \\ Pred"
    classes_header = " | ".join([f"{c[:6]:<6}" for c in CLASSES])
    print(f"{header_label:<20} | {classes_header}")
    print("-" * 65)
    for idx, row in enumerate(conf_mat):
        row_str = " | ".join([f"{val:<6}" for val in row])
        print(f"{CLASSES[idx]:<20} | {row_str}")

    # Prepare metrics dictionary
    overall_correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
    acc_ci = wilson_score_interval(overall_correct, len(y_true))

    metrics_summary = {
        "overall_accuracy": round(float(overall_acc), 4),
        "overall_accuracy_ci_95": acc_ci,
        "total_test_samples": len(y_true),
        "mean_confidence": round(float(np.mean(confidences)), 4),
        "per_class": {
            cls: {
                "precision": round(float(cls_report[cls]["precision"]), 4),
                "recall": round(float(cls_report[cls]["recall"]), 4),
                "f1_score": round(float(cls_report[cls]["f1-score"]), 4),
                "support": int(cls_report[cls]["support"]),
                "recall_ci_95": wilson_score_interval(
                    sum(1 for yt, yp in zip(y_true, y_pred) if yt == cls and yp == cls),
                    int(cls_report[cls]["support"])
                ),
            }
            for cls in CLASSES if cls in cls_report
        },
        "macro_avg": {
            "precision": round(float(cls_report["macro avg"]["precision"]), 4),
            "recall": round(float(cls_report["macro avg"]["recall"]), 4),
            "f1_score": round(float(cls_report["macro avg"]["f1-score"]), 4),
        },
        "weighted_avg": {
            "precision": round(float(cls_report["weighted avg"]["precision"]), 4),
            "recall": round(float(cls_report["weighted avg"]["recall"]), 4),
            "f1_score": round(float(cls_report["weighted avg"]["f1-score"]), 4),
        },
        "confusion_matrix": conf_mat.tolist(),
        "classes_order": CLASSES,
    }

    with open(METRICS_JSON_PATH, "w") as f:
        json.dump(metrics_summary, f, indent=2)

    return metrics_summary


if __name__ == "__main__":
    weight_file = train_classifier()
    evaluate_on_test_set(weight_file)
