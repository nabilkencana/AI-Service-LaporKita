"""
LaporKita Dataset Preparation & Unification Pipeline for 5-Class Classification.
Acquires verified public datasets, cleans, deduplicates, unifies labels,
and creates stratified 70/15/15 train/val/test splits in Ultralytics classification format.
"""

import os
import io
import hashlib
import random
import zipfile
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
import requests
import pandas as pd
from PIL import Image
from tqdm import tqdm

# Set fixed random seed for reproducibility
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "dataset"

# 5 Target Classes
CLASSES = [
    "Jalan Berlubang",
    "Trotoar",
    "Rambu Lalu Lintas",
    "Lampu Jalan",
    "Drainase",
]

DATASET_CONFIGS = {
    "Jalan Berlubang": [
        {
            "name": "keremberke/pothole-segmentation (train/val/test)",
            "urls": [
                "https://huggingface.co/datasets/keremberke/pothole-segmentation/resolve/main/data/train.zip",
                "https://huggingface.co/datasets/keremberke/pothole-segmentation/resolve/main/data/valid.zip",
                "https://huggingface.co/datasets/keremberke/pothole-segmentation/resolve/main/data/test.zip",
            ],
            "type": "zip_list",
            "license": "CC BY 4.0",
        },
        {
            "name": "Andyrasika/potholes-dataset (parquet train/val/test)",
            "type": "hf_parquet_potholes",
            "repo": "Andyrasika/potholes-dataset",
            "license": "MIT",
        }
    ],
    "Trotoar": [
        {
            "name": "mohammadnajeeb/concrete_crack_images (METU CCIC Positive)",
            "urls": [
                "https://huggingface.co/datasets/mohammadnajeeb/concrete_crack_images/resolve/main/data/train.zip",
            ],
            "type": "zip_filter",
            "filter_dir": "Positive",
            "max_samples": 600,
            "license": "CC BY 4.0",
        },
    ],
    "Rambu Lalu Lintas": [
        {
            "name": "keremberke/german-traffic-sign-detection (train/valid)",
            "urls": [
                "https://huggingface.co/datasets/keremberke/german-traffic-sign-detection/resolve/main/data/train.zip",
                "https://huggingface.co/datasets/keremberke/german-traffic-sign-detection/resolve/main/data/valid.zip",
            ],
            "type": "zip_list",
            "max_samples": 550,
            "license": "CC BY 4.0",
        },
    ],
    "Lampu Jalan": [
        {
            "name": "Team16Project/Street-Light-Dataset (GitHub)",
            "type": "github_tree",
            "repo": "Team16Project/Street-Light-Dataset",
            "path": "Resized Dataset",
            "max_samples": 450,
            "license": "MIT",
        }
    ],
    "Drainase": [
        {
            "name": "delima87/manhole_covers_dataset (train/valid)",
            "urls": [
                "https://huggingface.co/datasets/delima87/manhole_covers_dataset/resolve/main/manhole_covers_dataset/train.zip",
                "https://huggingface.co/datasets/delima87/manhole_covers_dataset/resolve/main/manhole_covers_dataset/valid.zip",
            ],
            "type": "zip_list",
            "max_samples": 550,
            "license": "CC BY 4.0",
        },
    ],
}


def compute_image_hash(img_bytes: bytes) -> str:
    """Compute MD5 hash to detect duplicate images."""
    return hashlib.md5(img_bytes).hexdigest()


def validate_and_load_image(img_bytes: bytes) -> Image.Image:
    """Verify image validity and convert to standard RGB."""
    try:
        img_io = io.BytesIO(img_bytes)
        with Image.open(img_io) as img:
            img.verify()
        # Re-open after verify
        img_io.seek(0)
        img = Image.open(img_io).convert("RGB")
        # Discard tiny images (< 32x32)
        if img.width < 32 or img.height < 32:
            return None
        return img
    except Exception:
        return None


def download_zip_urls(urls: List[str], filter_subfolder: str = None, max_samples: int = None) -> List[Tuple[str, bytes]]:
    """Download one or more zip archives and extract valid image bytes."""
    collected = []
    headers = {"User-Agent": "LaporKita-ML-Pipeline/1.0"}

    for url in urls:
        print(f"  Downloading zip from {url}...")
        r = requests.get(url, headers=headers, stream=True)
        if r.status_code != 200:
            print(f"  [ERROR] Failed to download {url}, status={r.status_code}")
            continue

        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            namelist = z.namelist()
            valid_names = [n for n in namelist if n.lower().endswith((".jpg", ".jpeg", ".png"))]
            if filter_subfolder:
                valid_names = [n for n in valid_names if filter_subfolder.lower() in n.lower()]

            for name in valid_names:
                img_bytes = z.read(name)
                collected.append((Path(name).name, img_bytes))

    if max_samples and len(collected) > max_samples:
        random.shuffle(collected)
        collected = collected[:max_samples]

    print(f"  Extracted {len(collected)} image files.")
    return collected


def download_hf_parquet_potholes(repo: str, max_samples: int = 500) -> List[Tuple[str, bytes]]:
    """Download images stored inside HuggingFace parquet files."""
    collected = []
    headers = {"User-Agent": "LaporKita-ML-Pipeline/1.0"}
    tree_url = f"https://huggingface.co/api/datasets/{repo}/tree/main/data"
    r = requests.get(tree_url, headers=headers)
    if r.status_code != 200:
        print(f"  [ERROR] Failed to read HF repo tree: {r.status_code}")
        return []

    files = [f["path"] for f in r.json() if f["path"].endswith(".parquet")]
    for fpath in files:
        url = f"https://huggingface.co/datasets/{repo}/resolve/main/{fpath}"
        print(f"  Downloading parquet from {url}...")
        p_res = requests.get(url, headers=headers)
        if p_res.status_code == 200:
            df = pd.read_parquet(io.BytesIO(p_res.content))
            for idx, row in df.iterrows():
                img_data = row.get("image")
                if isinstance(img_data, dict) and "bytes" in img_data:
                    b = img_data["bytes"]
                    collected.append((f"parquet_{Path(fpath).stem}_{idx}.jpg", b))
                elif isinstance(img_data, bytes):
                    collected.append((f"parquet_{Path(fpath).stem}_{idx}.jpg", img_data))

    if max_samples and len(collected) > max_samples:
        random.shuffle(collected)
        collected = collected[:max_samples]

    print(f"  Extracted {len(collected)} image files from parquet.")
    return collected


def download_github_tree_images(repo: str, subfolder: str, max_samples: int = 450) -> List[Tuple[str, bytes]]:
    """Download images recursively from a GitHub repository directory."""
    print(f"  Querying GitHub API for repo: {repo}/{subfolder}...")
    api_url = f"https://api.github.com/repos/{repo}/contents/{subfolder.replace(' ', '%20')}"
    headers = {"User-Agent": "LaporKita-ML-Pipeline/1.0"}
    r = requests.get(api_url, headers=headers)
    if r.status_code != 200:
        print(f"  [ERROR] GitHub API failed: {r.status_code}")
        return []

    collected = []
    items = r.json()
    dirs_to_visit = [item for item in items if item["type"] == "dir"]
    files = [item for item in items if item["type"] == "file"]

    for d in dirs_to_visit:
        sub_r = requests.get(d["url"], headers=headers)
        if sub_r.status_code == 200:
            for item in sub_r.json():
                if item["type"] == "file" and item["name"].lower().endswith((".jpg", ".jpeg", ".png")):
                    files.append(item)

    if max_samples and len(files) > max_samples:
        random.shuffle(files)
        files = files[:max_samples]

    print(f"  Downloading {len(files)} files from GitHub...")
    for item in tqdm(files, desc="GitHub Download"):
        img_r = requests.get(item["download_url"], headers=headers)
        if img_r.status_code == 200:
            collected.append((item["name"], img_r.content))

    return collected


def process_and_split_dataset():
    """Main pipeline execution function."""
    print("=" * 60)
    print("LAPORKITA DATASET PIPELINE: ACQUISITION, CLEANING, AND SPLIT")
    print("=" * 60)

    # Prepare directories
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    for split in ["train", "val", "test"]:
        for cls_name in CLASSES:
            (OUTPUT_DIR / split / cls_name).mkdir(parents=True, exist_ok=True)

    stats = {
        cls_name: {
            "raw_downloaded": 0,
            "corrupted_removed": 0,
            "duplicates_removed": 0,
            "clean_total": 0,
            "train": 0,
            "val": 0,
            "test": 0,
        }
        for cls_name in CLASSES
    }

    for cls_name, configs in DATASET_CONFIGS.items():
        print(f"\nProcessing class: [{cls_name}]")
        seen_hashes = set()
        clean_images = []

        for cfg in configs:
            print(f"- Source: {cfg['name']}")
            raw_list = []
            if cfg["type"] in ["zip_list", "zip_filter"]:
                raw_list = download_zip_urls(
                    urls=cfg.get("urls", [cfg.get("url")]),
                    filter_subfolder=cfg.get("filter_dir"),
                    max_samples=cfg.get("max_samples"),
                )
            elif cfg["type"] == "hf_parquet_potholes":
                raw_list = download_hf_parquet_potholes(
                    repo=cfg["repo"],
                    max_samples=cfg.get("max_samples", 500),
                )
            elif cfg["type"] == "github_tree":
                raw_list = download_github_tree_images(
                    repo=cfg["repo"],
                    subfolder=cfg["path"],
                    max_samples=cfg.get("max_samples", 450),
                )

            stats[cls_name]["raw_downloaded"] += len(raw_list)

            # Clean and deduplicate
            for filename, img_bytes in raw_list:
                img_hash = compute_image_hash(img_bytes)
                if img_hash in seen_hashes:
                    stats[cls_name]["duplicates_removed"] += 1
                    continue

                img = validate_and_load_image(img_bytes)
                if img is None:
                    stats[cls_name]["corrupted_removed"] += 1
                    continue

                seen_hashes.add(img_hash)
                clean_images.append((filename, img))

        stats[cls_name]["clean_total"] = len(clean_images)
        print(f"-> Total clean & unique images for '{cls_name}': {len(clean_images)}")

        # Stratified Split 70% Train / 15% Val / 15% Test
        random.shuffle(clean_images)
        n = len(clean_images)
        n_train = int(0.70 * n)
        n_val = int(0.15 * n)
        n_test = n - n_train - n_val

        train_set = clean_images[:n_train]
        val_set = clean_images[n_train:n_train + n_val]
        test_set = clean_images[n_train + n_val:]

        stats[cls_name]["train"] = len(train_set)
        stats[cls_name]["val"] = len(val_set)
        stats[cls_name]["test"] = len(test_set)

        # Save to Ultralytics classification structure
        for split_name, dataset_part in [("train", train_set), ("val", val_set), ("test", test_set)]:
            target_dir = OUTPUT_DIR / split_name / cls_name
            for idx, (fname, img) in enumerate(dataset_part):
                stem = Path(fname).stem
                out_path = target_dir / f"{cls_name.lower().replace(' ', '_')}_{idx:05d}_{stem}.jpg"
                img.save(out_path, format="JPEG", quality=92)

    print("\n" + "=" * 60)
    print("FINAL DATASET SPLIT SUMMARY")
    print("=" * 60)
    print(f"{'Class':<20} | {'Raw':<6} | {'Corrupt':<8} | {'Dupes':<6} | {'Clean':<6} | {'Train':<6} | {'Val':<6} | {'Test':<6}")
    print("-" * 80)
    for cls_name, s in stats.items():
        print(f"{cls_name:<20} | {s['raw_downloaded']:<6} | {s['corrupted_removed']:<8} | {s['duplicates_removed']:<6} | {s['clean_total']:<6} | {s['train']:<6} | {s['val']:<6} | {s['test']:<6}")

    return stats


if __name__ == "__main__":
    process_and_split_dataset()
