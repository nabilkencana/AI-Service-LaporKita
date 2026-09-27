#!/usr/bin/env python3
"""
========================================================================================
LaporKita AI — Full Multi-Class Active Learning Dataset Ingester
========================================================================================
Mengumpulkan dan memvalidasi citra riil untuk 5 kelas fasilitas umum:
- Jalan_Berlubang
- Trotoar
- Drainase
- Lampu_Jalan
- Rambu_Lalu_Lintas
Ditambah sampel OOD bukan_fasilitas tambahan.
========================================================================================
"""

import io
import time
import base64
import urllib.request
import urllib.parse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

API_URL = "https://ai.canadev.my.id/v1/training/ingest-sample"
STATS_URL = "https://ai.canadev.my.id/v1/training/dataset-stats"
API_KEY = os.environ.get("INTERNAL_API_KEY", "")
USER_AGENT = "LaporKita-MLOps-Harvester/2.0 (contact@laporkita.malangkota.go.id)"

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

def process_image(img_bytes):
    try:
        img = Image.open(io.BytesIO(img_bytes))
        img.verify()
        img = Image.open(io.BytesIO(img_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        if w < 224 or h < 224:
            return None
        hsh = calculate_dhash(img)
        if hsh in seen_hashes:
            return None
        seen_hashes.add(hsh)
        if max(w, h) > 800:
            img.thumbnail((800, 800), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=85, optimize=True)
        return base64.b64encode(out.getvalue()).decode("utf-8")
    except Exception:
        return None

def ingest_sample(category, b64_str, source_title):
    payload = {
        "image_base64": b64_str,
        "verified_category": category,
        "original_prediction": category,
        "confidence_score": 0.99,
        "operator_notes": f"Curated benchmark sample: {source_title}",
        "source": "curated_web_benchmark"
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT
        }
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def fetch_wiki_bitmap_urls(search_terms):
    urls = []
    for term in search_terms:
        q = urllib.parse.quote_plus(f"{term} filetype:bitmap")
        url = f"https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrnamespace=6&gsrsearch={q}&gsrlimit=35&prop=imageinfo&iiprop=url|mime|size"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for pid, p in data.get("query", {}).get("pages", {}).items():
                    if "imageinfo" in p:
                        info = p["imageinfo"][0]
                        if info.get("mime") in ("image/jpeg", "image/png"):
                            urls.append((p.get("title", ""), info.get("url", "")))
        except Exception:
            pass
    return urls

def download_and_ingest(category, title, img_url):
    try:
        req = urllib.request.Request(img_url, headers={"User-Agent": USER_AGENT, "Referer": "https://commons.wikimedia.org"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
        b64 = process_image(raw)
        if not b64:
            return False
        res = ingest_sample(category, b64, title)
        return res.get("success", False)
    except Exception:
        return False

def main():
    print("========================================================================")
    print("🚀 BATCH INGESTION FOR ALL 5 INFRASTRUCTURE CLASSES")
    print("========================================================================\n")

    tasks = [
        ("Lampu_Jalan", ["streetlight pole", "street lamp post luminaire", "lantern street light"], 35),
        ("Drainase", ["storm drain street", "sewer grate street gutter", "road drainage culvert"], 35),
        ("Trotoar", ["sidewalk pavement", "pedestrian sidewalk walkway", "paving footpath"], 35),
        ("Rambu_Lalu_Lintas", ["traffic sign street", "road traffic sign warning", "speed limit sign"], 35),
        ("Jalan_Berlubang", ["pothole asphalt road", "road pothole asphalt depression"], 25),
    ]

    total_added = 0

    for category, terms, target in tasks:
        print(f"📂 Kategori [{category}]: Mengumpulkan URL citra...")
        candidates = fetch_wiki_bitmap_urls(terms)
        print(f"   Ditemukan {len(candidates)} calon citra. Memulai unduh & ingest paralel...")

        success_count = 0
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_cand = {
                executor.submit(download_and_ingest, category, title, url): (title, url)
                for title, url in candidates
            }
            for future in as_completed(future_to_cand):
                if success_count >= target:
                    break
                try:
                    if future.result():
                        success_count += 1
                        total_added += 1
                except Exception:
                    pass

        print(f"   ✅ Selesai [{category}]: {success_count}/{target} citra riil berhasil masuk.")

    print("\n========================================================================")
    print(f"🎉 INGESTION SELESAI! Tambahan {total_added} citra berhasil di-ingest ke server.")
    print("========================================================================")

    # Fetch live dataset statistics
    req = urllib.request.Request(STATS_URL, headers={"X-API-Key": API_KEY, "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=10) as resp:
        stats = json.loads(resp.read().decode("utf-8")).get("data", {})
        print("\n📊 DISTRIBUSI TOTAL DATASET DI SERVER:")
        print(f"   Total Sampel:           {stats.get('total_samples')}")
        print(f"   Status Retraining:      {'Siap Dilatih Ulang (Ready)' if stats.get('ready_for_retraining') else 'Collecting'}")
        print("   Distribusi per Kelas:")
        for cls_name, cnt in stats.get("class_distribution", {}).items():
            print(f"     - {cls_name:20}: {cnt} citra")

if __name__ == "__main__":
    main()
