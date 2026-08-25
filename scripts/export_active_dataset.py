#!/usr/bin/env python3
"""
========================================================================================
Dataset Split & Exporter for Active Learning (YOLOv11-cls format)
========================================================================================
Splits gathered samples into:
  - dataset/split/train (80%)
  - dataset/split/val   (10%)
  - dataset/split/test  (10%)
========================================================================================
"""

import os
import shutil
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE_DIR = BASE_DIR / "data" / "active_learning" / "labeled"
OUTPUT_DIR = BASE_DIR / "data" / "active_learning" / "split"

TRAIN_RATIO = 0.8
VAL_RATIO = 0.1
TEST_RATIO = 0.1


def export_dataset():
    if not SOURCE_DIR.exists():
        print(f"Source directory {SOURCE_DIR} does not exist yet.")
        return

    print(f"Starting dataset export from {SOURCE_DIR} -> {OUTPUT_DIR}...")

    # Clear previous split
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    for split in ["train", "val", "test"]:
        for cls_dir in SOURCE_DIR.iterdir():
            if cls_dir.is_dir():
                (OUTPUT_DIR / split / cls_dir.name).mkdir(parents=True, exist_ok=True)

    total_exported = 0

    for cls_dir in SOURCE_DIR.iterdir():
        if not cls_dir.is_dir():
            continue

        images = list(cls_dir.glob("*.jpg")) + list(cls_dir.glob("*.png")) + list(cls_dir.glob("*.jpeg"))
        random.shuffle(images)

        n = len(images)
        n_train = int(n * TRAIN_RATIO)
        n_val = int(n * VAL_RATIO)

        train_imgs = images[:n_train]
        val_imgs = images[n_train : n_train + n_val]
        test_imgs = images[n_train + n_val :]

        for img in train_imgs:
            shutil.copy2(img, OUTPUT_DIR / "train" / cls_dir.name / img.name)
        for img in val_imgs:
            shutil.copy2(img, OUTPUT_DIR / "val" / cls_dir.name / img.name)
        for img in test_imgs:
            shutil.copy2(img, OUTPUT_DIR / "test" / cls_dir.name / img.name)

        print(f"[{cls_dir.name}] Total: {n} (Train: {len(train_imgs)}, Val: {len(val_imgs)}, Test: {len(test_imgs)})")
        total_exported += n

    print(f"\nExport complete! {total_exported} images structured in YOLOv11 format at {OUTPUT_DIR}")


if __name__ == "__main__":
    export_dataset()
