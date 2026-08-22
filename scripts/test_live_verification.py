"""
Live End-to-End Verification Test against running FastAPI server using real test photos.
"""

import base64
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TEST_DIR = BASE_DIR / "dataset" / "test"

API_URL = "http://127.0.0.1:8000/v1/verify"
CLASSES = ["Jalan Berlubang", "Trotoar", "Rambu Lalu Lintas", "Lampu Jalan", "Drainase"]


def test_real_photos():
    print("=" * 70)
    print("LIVE END-TO-END VERIFICATION WITH REAL TEST SET IMAGES")
    print("=" * 70)

    for cls in CLASSES:
        cls_dir = TEST_DIR / cls
        images = list(cls_dir.glob("*.jpg"))
        if not images:
            print(f"No test images found for {cls}")
            continue

        sample_img = images[0]
        with open(sample_img, "rb") as f:
            b64_str = base64.b64encode(f.read()).decode("utf-8")

        from datetime import datetime, timezone
        payload = {
            "image_base64": b64_str,
            "claimed_category": cls,
            "latitude": -7.9826,  # Alun-Alun Malang
            "longitude": 112.6308,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        resp = requests.post(API_URL, json=payload, timeout=10)
        print(f"\n[Test Sample: {cls}] -> File: {sample_img.name}")
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            print(f"  Predicted Category : {data.get('predicted_category')}")
            print(f"  AI Confidence Score: {data.get('ai_confidence_score') * 100:.2f}%")
            print(f"  Is Valid           : {data.get('is_valid')}")
            print(f"  Needs Manual Review: {data.get('needs_manual_review')}")
            print(f"  Damage Severity    : {data.get('damage_severity')}")
            print(f"  Urgency Score      : {data.get('urgency_score')}")
            print(f"  Auto Description   : {data.get('description_auto')}")
        else:
            print(f"  Error: {resp.text}")


if __name__ == "__main__":
    test_real_photos()
