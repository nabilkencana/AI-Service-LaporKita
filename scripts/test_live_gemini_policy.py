"""
Live End-to-End Test for Policy Simulator with Real Google Gemini API.
"""

import json
import requests

API_URL = "http://127.0.0.1:8000/v1/policy-simulate"


def test_live_gemini_simulation():
    print("=" * 70)
    print("LIVE POLICY SIMULATOR TEST WITH REAL GEMINI 2.5 API")
    print("=" * 70)

    payload = {
        "prompt_text": "Bagaimana proyeksi dampak jika Pemkot Malang mengalokasikan anggaran Rp 1.5 Miliar untuk normalisasi gorong-gorong dan pengerukan sedimentasi drainase di sepanjang koridor Jalan Soekarno-Hatta (Kecamatan Lowokwaru) menjelang musim hujan?",
        "zone_id": "zone-lowokwaru-suhat",
        "time_horizon_months": 6,
        "parameters": {
            "allocated_budget_idr": 1500000000,
            "target_district": "Lowokwaru",
            "priority_facility": "Drainase",
        }
    }

    print(f"\n[REQUEST PAYLOAD]:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")
    print("\nSending request to FastAPI server...")

    resp = requests.post(API_URL, json=payload, timeout=30)
    print(f"\nHTTP Status Code: {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        print("\n" + "=" * 70)
        print("PARSED STRUCTURED RESPONSE FROM GEMINI:")
        print("=" * 70)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"Error Response: {resp.text}")


if __name__ == "__main__":
    test_live_gemini_simulation()
