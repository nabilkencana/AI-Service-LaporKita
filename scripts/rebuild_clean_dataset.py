"""
Rebuild clean, leak-free dataset split for LaporKita 5-class classifier.
Implements perceptual hash (dHash) clustering + sequence grouping (LEAK-1 fix)
so that near-duplicate and same-video images are strictly kept within the same split.
"""

import os
import shutil
from pathlib import Path
from collections import defaultdict
import numpy as np
from PIL import Image
import random
import re

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "dataset"
STAGING_DIR = BASE_DIR / "dataset_staging"
CLASSES = [
    "Drainase",
    "Jalan Berlubang",
    "Lampu Jalan",
    "Rambu Lalu Lintas",
    "Trotoar",
    "bukan_fasilitas",
]


def compute_dhash(img: Image.Image, hash_size: int = 8) -> np.ndarray:
    """Compute 64-bit difference hash."""
    resized = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = np.array(resized)
    return (pixels[:, 1:] > pixels[:, :-1]).flatten()


def get_sequence_group_key(filename: str) -> str:
    """Extract sequence group from filenames like ...parquet_train-00000-of-00001-..._152.jpg"""
    # If synthetic solid color or noise group
    if "solid_color" in filename:
        return "solid_color_all"
    
    # If parquet file with frame number
    m = re.search(r"(parquet_[a-zA-Z0-9_\-]+)_(\d+)", filename)
    if m:
        group_base = m.group(1)
        frame_idx = int(m.group(2))
        # Group adjacent frames within 15 frames of each other
        bucket = frame_idx // 15
        return f"{group_base}_bucket_{bucket}"
    
    # If WhatsApp / Camera burst photo
    m_wa = re.search(r"(WhatsApp Image \d{4}-\d{2}-\d{2} at \d{2}\.\d{2})", filename)
    if m_wa:
        return m_wa.group(1)
    
    m_img = re.search(r"(IMG_\d{8}_\d{4})", filename)
    if m_img:
        return m_img.group(1)

    return filename


class DisjointSet:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, i):
        if self.parent[i] == i:
            return i
        self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i, j):
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            self.parent[root_i] = root_j


def rebuild_splits():
    print("=" * 60)
    print("REBUILDING CLEAN, LEAK-FREE 6-CLASS DATASET (FIX-1 OOD)")
    print("=" * 60)

    # 1. Collect all existing clean images across train, val, test and dataset_staging
    raw_images_per_class = defaultdict(list)
    
    for split in ["train", "val", "test"]:
        split_dir = DATASET_DIR / split
        if not split_dir.exists():
            continue
        for cls_name in CLASSES:
            cls_dir = split_dir / cls_name
            if cls_dir.exists():
                for p in cls_dir.glob("*.jpg"):
                    try:
                        with Image.open(p) as img:
                            img_rgb = img.convert("RGB")
                            d_h = compute_dhash(img_rgb)
                            raw_images_per_class[cls_name].append({
                                "path": p,
                                "name": p.name,
                                "image": img_rgb,
                                "hash": d_h,
                                "seq_key": get_sequence_group_key(p.name),
                            })
                    except Exception as e:
                        print(f"Skipping corrupt image {p}: {e}")

    # Also collect from dataset_staging/bukan_fasilitas if not already collected
    staging_ood = STAGING_DIR / "bukan_fasilitas"
    if staging_ood.exists() and len(raw_images_per_class["bukan_fasilitas"]) == 0:
        print(f"Loading negative/OOD images from staging directory {staging_ood}...")
        for p in staging_ood.glob("*.jpg"):
            try:
                with Image.open(p) as img:
                    img_rgb = img.convert("RGB")
                    d_h = compute_dhash(img_rgb)
                    raw_images_per_class["bukan_fasilitas"].append({
                        "path": p,
                        "name": p.name,
                        "image": img_rgb,
                        "hash": d_h,
                        "seq_key": get_sequence_group_key(p.name),
                    })
            except Exception as e:
                print(f"Skipping corrupt staging image {p}: {e}")

    # Remove old splits and cache
    for cache_file in DATASET_DIR.glob("*.cache"):
        cache_file.unlink()
    shutil.rmtree(DATASET_DIR / "train", ignore_errors=True)
    shutil.rmtree(DATASET_DIR / "val", ignore_errors=True)
    shutil.rmtree(DATASET_DIR / "test", ignore_errors=True)

    for split in ["train", "val", "test"]:
        for cls_name in CLASSES:
            (DATASET_DIR / split / cls_name).mkdir(parents=True, exist_ok=True)

    stats = {}

    for cls_name in CLASSES:
        items = raw_images_per_class[cls_name]
        n_items = len(items)
        print(f"\nProcessing class '{cls_name}': {n_items} images total")

        # Build clusters using DSU
        dsu = DisjointSet(n_items)

        # 2a. Cluster by perceptual hash (dHash distance <= 8)
        hashes = np.array([item["hash"] for item in items])
        for i in range(n_items):
            # Vectorized hamming distance against all subsequent items
            dists = np.count_nonzero(hashes[i:] != hashes[i], axis=1)
            for offset, d in enumerate(dists):
                j = i + offset
                if i != j and d <= 8:  # Strict perceptual similarity threshold
                    dsu.union(i, j)

        # 2b. Cluster by sequence / video group
        seq_groups = defaultdict(list)
        for i, item in enumerate(items):
            seq_groups[item["seq_key"]].append(i)

        for key, indices in seq_groups.items():
            if len(indices) > 1:
                first = indices[0]
                for idx in indices[1:]:
                    dsu.union(first, idx)

        # 3. Group items by their cluster root
        clusters = defaultdict(list)
        for i in range(n_items):
            root = dsu.find(i)
            clusters[root].append(items[i])

        cluster_list = list(clusters.values())
        # Shuffle clusters with fixed seed
        random.seed(RANDOM_SEED)
        random.shuffle(cluster_list)

        print(f"  Formed {len(cluster_list)} independent clusters from {n_items} images.")

        # 4. Allocate clusters to train / val / test (target ~70% / 15% / 15%)
        target_train = int(0.70 * n_items)
        target_val = int(0.15 * n_items)

        train_items = []
        val_items = []
        test_items = []

        for cluster in cluster_list:
            if len(train_items) + len(cluster) <= target_train:
                train_items.extend(cluster)
            elif len(val_items) + len(cluster) <= target_val:
                val_items.extend(cluster)
            else:
                test_items.extend(cluster)

        # If test or val is slightly under/over, balance gently
        if len(test_items) < int(0.10 * n_items):
            # Take last cluster from train if train has excess
            if len(train_items) > target_train and cluster_list:
                for c in reversed(cluster_list):
                    if c[0] in train_items and len(train_items) - len(c) >= int(0.65 * n_items):
                        for x in c:
                            train_items.remove(x)
                            test_items.append(x)
                        break

        print(f"  Split counts -> Train: {len(train_items)}, Val: {len(val_items)}, Test: {len(test_items)}")

        # 5. Save cleanly
        for split_name, item_list in [("train", train_items), ("val", val_items), ("test", test_items)]:
            target_dir = DATASET_DIR / split_name / cls_name
            for idx, item in enumerate(item_list):
                stem = Path(item["name"]).stem
                out_path = target_dir / f"{cls_name.lower().replace(' ', '_')}_{idx:05d}_{stem}.jpg"
                item["image"].save(out_path, format="JPEG", quality=92)

        stats[cls_name] = {
            "total": n_items,
            "clusters": len(cluster_list),
            "train": len(train_items),
            "val": len(val_items),
            "test": len(test_items),
        }

    # 6. Run verification
    print("\n" + "=" * 60)
    print("LEAKAGE VERIFICATION (Train <-> Test)")
    print("=" * 60)

    train_h = []
    test_h = []
    for cls_name in CLASSES:
        for p in (DATASET_DIR / "train" / cls_name).glob("*.jpg"):
            with Image.open(p) as img:
                train_h.append((cls_name, compute_dhash(img)))
        for p in (DATASET_DIR / "test" / cls_name).glob("*.jpg"):
            with Image.open(p) as img:
                test_h.append((cls_name, compute_dhash(img)))

    leak_d4 = 0
    leak_d8 = 0
    for t_cls, t_hash in test_h:
        for tr_cls, tr_hash in train_h:
            if t_cls == tr_cls:
                dist = np.count_nonzero(t_hash != tr_hash)
                if dist <= 4:
                    leak_d4 += 1
                if dist <= 8:
                    leak_d8 += 1

    print(f"Total Train images: {len(train_h)}")
    print(f"Total Test images: {len(test_h)}")
    print(f"Train <-> Test pairs with dHash <= 4: {leak_d4} (EXPECTED: 0)")
    print(f"Train <-> Test pairs with dHash <= 8: {leak_d8} (EXPECTED: 0)")

    return stats


if __name__ == "__main__":
    rebuild_splits()
