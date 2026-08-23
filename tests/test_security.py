import asyncio
import base64
import io
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from PIL import Image


@pytest.mark.asyncio
async def test_ssrf_protection_loopback_url(client: AsyncClient):
    """
    Scenario (SEC-SSRF): Attempt to supply a loopback/internal URL to image_url.
    Expected: HTTP 422 with INVALID_IMAGE and SSRF protection error message.
    """
    payload = {
        "image_url": "http://127.0.0.1:9999/internal-secret.jpg",
        "claimed_category": "Trotoar",
        "latitude": -7.9826,
        "longitude": 112.6308,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    response = await client.post("/v1/verify", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_IMAGE"
    assert "SSRF Protection" in data["error"]["message"]


@pytest.mark.asyncio
async def test_ssrf_protection_cloud_metadata_url(client: AsyncClient):
    """
    Scenario (SEC-SSRF): Attempt to access cloud instance metadata endpoint.
    Expected: HTTP 422 with INVALID_IMAGE and SSRF protection error.
    """
    payload = {
        "image_url": "http://169.254.169.254/latest/meta-data/",
        "claimed_category": "Jalan Berlubang",
        "latitude": -7.9826,
        "longitude": 112.6308,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    response = await client.post("/v1/verify", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert "SSRF Protection" in data["error"]["message"]


@pytest.mark.asyncio
async def test_local_file_path_in_image_url_rejected(client: AsyncClient):
    """
    Scenario (SEC-SSRF): Attempt to supply a local filesystem path as image_url.
    Expected: HTTP 422 with scheme rejection.
    """
    payload = {
        "image_url": "/etc/passwd",
        "claimed_category": "Jalan Berlubang",
        "latitude": -7.9826,
        "longitude": 112.6308,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    response = await client.post("/v1/verify", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert "tidak didukung" in data["error"]["message"]


@pytest.mark.asyncio
async def test_oversized_image_rejected(client: AsyncClient):
    """
    Scenario (SEC-SIZE): Attempt to upload oversized image > 8MB.
    Expected: HTTP 422 rejected.
    """
    # Create fake oversized bytes (8.5 MB)
    oversized_bytes = b"0" * (9 * 1024 * 1024)
    oversized_b64 = base64.b64encode(oversized_bytes).decode("utf-8")

    payload = {
        "image_base64": oversized_b64,
        "claimed_category": "Jalan Berlubang",
        "latitude": -7.9826,
        "longitude": 112.6308,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    response = await client.post("/v1/verify", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert "melebihi batas maksimum" in data["error"]["message"]


@pytest.mark.asyncio
async def test_low_resolution_image_rejected_res480(client: AsyncClient):
    """
    Scenario (RES-480): Attempt to submit a low-resolution image < 200px longest edge.
    Expected: HTTP 422 with clear resolution error message.
    """
    img = Image.new("RGB", (120, 120), color=(100, 100, 100))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    payload = {
        "image_base64": img_b64,
        "claimed_category": "Jalan Berlubang",
        "latitude": -7.9826,
        "longitude": 112.6308,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    response = await client.post("/v1/verify", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert "terlalu rendah" in data["error"]["message"]
    assert "200" in data["error"]["message"]


@pytest.mark.asyncio
async def test_internal_api_key_auth_enforcement(client: AsyncClient):
    """
    Scenario (SEC-NOAUTH): Verify X-API-Key header enforcement when INTERNAL_API_KEY is configured.
    """
    from app.core.config import settings
    original_key = settings.INTERNAL_API_KEY
    test_secret = "laporkita-test-secret-key-999"

    try:
        settings.INTERNAL_API_KEY = test_secret

        img = Image.new("RGB", (480, 480), color=(100, 150, 200))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        payload = {
            "image_base64": img_b64,
            "claimed_category": "Trotoar",
            "latitude": -7.9826,
            "longitude": 112.6308,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # 1. Without header -> 401 Unauthorized
        from httpx import ASGITransport
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as raw_client:
            res_no_key = await raw_client.post("/v1/verify", json=payload)
            assert res_no_key.status_code == 401

            # 2. With invalid header -> 403 Forbidden
            res_wrong_key = await raw_client.post("/v1/verify", json=payload, headers={"X-API-Key": "wrong-key"})
            assert res_wrong_key.status_code == 403

            # 3. With valid X-API-Key -> 200 OK
            res_valid_key = await raw_client.post("/v1/verify", json=payload, headers={"X-API-Key": test_secret})
            assert res_valid_key.status_code == 200

            # 4. /health must remain public without auth -> 200 OK
            res_health = await raw_client.get("/health")
            assert res_health.status_code == 200

    finally:
        settings.INTERNAL_API_KEY = original_key


@pytest.mark.asyncio
async def test_concurrent_requests_non_blocking(client: AsyncClient):
    """
    Scenario (CONC-1): Fire 10 concurrent requests to verify non-blocking event loop execution.
    Expected: All 10 succeed simultaneously.
    """
    # Create a valid 480x480 image
    img = Image.new("RGB", (480, 480), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    payload = {
        "image_base64": img_b64,
        "claimed_category": "Trotoar",
        "latitude": -7.9826,
        "longitude": 112.6308,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    tasks = [client.post("/v1/verify", json=payload) for _ in range(10)]
    responses = await asyncio.gather(*tasks)

    for r in responses:
        assert r.status_code == 200
        assert r.json()["success"] is True
