#!/usr/bin/env python3
"""
Fast parallel completion of remaining categories, split, and YOLOv11 retraining.
"""

import io
import time
import base64
import urllib.request
import urllib.parse
import json
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "active_learning"
LABELED_DIR = DATA_DIR / "labeled"
SPLIT_DIR = DATA_DIR / "split"
OUTPUT_MODEL_DIR = BASE_DIR / "app" / "models" / "active_learning_runs"

API_URL = "https://ai.canadev.my.id/v1/training/ingest-sample"
API_KEY = os.environ.get("INTERNAL_API_KEY", "")
USER_AGENT = "LaporKita-MLOps-Harvester/2.0 (contact@laporkita.malangkota.go.id)"

VALID_CLASSES = [
    "Jalan_Berlubang",
    "Trotoar",
    "Drainase",
    "Lampu_Jalan",
    "Rambu_Lalu_Lintas",
    "bukan_fasilitas",
]

seen_hashes = set()

def calculate_dhash(img, hash_size=8):
    resized = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    diff = []
    for row in range(hash_size):
        for col in range(hash_size):
            pixel_left = resized.getpixel((col, row))
            pixel_right = resized.getpixel((col + 1, row))
            diff.append(pixel_left > pixel_right)
    return "".join("1" if b else "0" for b in diff)

def process_and_save_locally(img_bytes, category, filename_prefix):
    try:
        img = Image.open(io.BytesIO(img_bytes))
        img.verify()
        img = Image.open(io.BytesIO(img_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        if w < 224 or h < 224:
            return None, None
        hsh = calculate_dhash(img)
        if hsh in seen_hashes:
            return None, None
        seen_hashes.add(hsh)
        if max(w, h) > 800:
            img.thumbnail((800, 800), Image.Resampling.LANCZOS)

        cat_dir = LABELED_DIR / category
        cat_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{filename_prefix}_{int(time.time()*1000)%1000000}_{len(seen_hashes)}.jpg"
        save_path = cat_dir / filename
        img.save(save_path, format="JPEG", quality=85, optimize=True)

        out_io = io.BytesIO()
        img.save(out_io, format="JPEG", quality=85)
        b64 = base64.b64encode(out_io.getvalue()).decode("utf-8")
        return b64, filename
    except Exception:
        return None, None

def ingest_to_server(category, b64_str, title):
    try:
        payload = {
            "image_base64": b64_str,
            "verified_category": category,
            "original_prediction": category,
            "confidence_score": 0.99,
            "operator_notes": f"Curated: {title}",
            "source": "curated_web_benchmark"
        }
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"X-API-Key": API_KEY, "Content-Type": "application/json", "User-Agent": USER_AGENT}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

def fetch_wiki_urls(search_terms, max_items):
    urls = []
    for term in search_terms:
        q = urllib.parse.quote_plus(f"{term} filetype:bitmap")
        url = f"https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrnamespace=6&gsrsearch={q}&gsrlimit={max_items}&prop=imageinfo&iiprop=url|mime|size"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for pid, p in data.get("query", {}).get("pages", {}).items():
                    if "imageinfo" in p:
                        info = p["imageinfo"][0]
                        if info.get("mime") in ("image/jpeg", "image/png"):
                            urls.append((p.get("title", ""), info.get("url", "")))
        except Exception:
            pass
    return urls

def fetch_single_and_save(category, title, img_url):
    try:
        req = urllib.request.Request(img_url, headers={"User-Agent": USER_AGENT, "Referer": "https://commons.wikimedia.org"})
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read()
        b64, fname = process_and_save_locally(raw, category, f"wiki_{category}")
        if b64:
            ingest_to_server(category, b64, title)
            return True
    except Exception:
        pass
    return False

def complete_remaining():
    remaining_tasks = [
        ("Drainase", ["storm drain grate", "street sewer drain", "drainage grate road"], 40),
        ("Lampu_Jalan", ["streetlight pole street", "street lamp post luminaire", "lantern streetlight"], 40),
        ("Rambu_Lalu_Lintas", ["traffic road sign warning", "street regulatory traffic sign", "speed limit sign"], 40),
    ]

    for category, terms, target in remaining_tasks:
        existing = len(list((LABELED_DIR / category).glob("*.jpg")))
        needed = max(0, target - existing)
        if needed == 0:
            print(f"[{category}] Sudah lengkap: {existing} citra.")
            continue

        print(f"[{category}] Mengumpulkan {needed} citra tambahan...")
        candidates = fetch_wiki_urls(terms, needed * 3)
        print(f"   Ditemukan {len(candidates)} kandidat. Memulai download paralel...")

        got = 0
        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = [ex.submit(fetch_single_and_save, category, title, url) for title, url in candidates]
            for f in as_completed(futs):
                if got >= needed:
                    break
                try:
                    if f.result():
                        got += 1
                except Exception:
                    pass
        print(f"   ✅ Selesai [{category}]: Total sekarang = {len(list((LABELED_DIR / category).glob('*.jpg')))} citra.")

def split_dataset():
    print("\n========================================================================")
    print("✂️ TAHAP 2: EXPORT & SPLIT DATASET (TRAIN 80% / VAL 10% / TEST 10%)")
    print("========================================================================\n")

    if SPLIT_DIR.exists():
        shutil.rmtree(SPLIT_DIR)

    for split in ["train", "val", "test"]:
        for c in VALID_CLASSES:
            (SPLIT_DIR / split / c).mkdir(parents=True, exist_ok=True)

    total_split = 0
    for cls_dir in LABELED_DIR.iterdir():
        if not cls_dir.is_dir() or cls_dir.name not in VALID_CLASSES:
            continue
        imgs = list(cls_dir.glob("*.jpg"))
        import random
        random.shuffle(imgs)
        n = len(imgs)
        n_train = max(1, int(n * 0.8))
        n_val = max(1, int(n * 0.1))
        train_imgs = imgs[:n_train]
        val_imgs = imgs[n_train:n_train+n_val]
        test_imgs = imgs[n_train+n_val:]

        for im in train_imgs:
            shutil.copy2(im, SPLIT_DIR / "train" / cls_dir.name / im.name)
        for im in val_imgs:
            shutil.copy2(im, SPLIT_DIR / "val" / cls_dir.name / im.name)
        for im in test_imgs:
            shutil.copy2(im, SPLIT_DIR / "test" / cls_dir.name / im.name)

        print(f"   [{cls_dir.name:20}] Total: {n:3d} (Train: {len(train_imgs):3d}, Val: {len(val_imgs):2d}, Test: {len(test_imgs):2d})")
        total_split += n

    print(f"\n✅ Split selesai! Total {total_split} citra terdistribusi ke {SPLIT_DIR}")

def train_yolo(epochs=15, batch_size=16):
    print("\n========================================================================")
    print(f"🏋️ TAHAP 3: RETRAINING YOLOV11-CLS (EPOCHS={epochs}, BATCH={batch_size})")
    print("   Akselerasi Hardware: Apple Silicon Metal Performance Shaders (MPS GPU)")
    print("========================================================================\n")

    from ultralytics import YOLO
    import torch

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"🖥️ Using compute device: {device.upper()}")

    base_weights = BASE_DIR / "models" / "yolov11-cls-laporkita.pt"
    if not base_weights.exists():
        base_weights = BASE_DIR / "yolo11n-cls.pt"

    print(f"📦 Loading pre-trained base model: {base_weights}")
    model = YOLO(str(base_weights))

    OUTPUT_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    results = model.train(
        data=str(SPLIT_DIR),
        epochs=epochs,
        imgsz=224,
        batch=batch_size,
        device=device,
        project=str(OUTPUT_MODEL_DIR),
        name="retrain_run_v1",
        exist_ok=True,
        verbose=True,
        degrees=45.0,
        fliplr=0.5,
        flipud=0.5,
    )

    best_weights = OUTPUT_MODEL_DIR / "retrain_run_v1" / "weights" / "best.pt"
    print("\n========================================================================")
    print("🎉 RETRAINING SELESAI DENGAN SUKSES!")
    print(f"📊 Model weights baru tersimpan di: {best_weights}")
    print("========================================================================")

if __name__ == "__main__":
    complete_remaining()
    split_dataset()
    train_yolo(epochs=12, batch_size=16)
